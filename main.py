from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import engine, Base, get_db
import model
import schemas
from auth import hash_password, verify_password, create_access_token, decode_access_token

Base.metadata.create_all(bind=engine)

app = FastAPI()
# Ye batata hai ke token kahan se login hoga
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Ye saare connected screens (clients) ko sambhalta hai
class ConnectionManager:
    def __init__(self):
        self.active = []   # jitne log connected hain

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        # sab connected screens ko ye message bhej do
        for conn in list(self.active):
            try:
                await conn.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()
# DARBAAN 1: Token check karke current user nikaalta hai
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token galat ya expire ho gaya")

    user_id = payload.get("user_id")
    user = db.query(model.User).filter(model.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User nahi mila")
    return user

# DARBAAN 2: Sirf admin ko aage jaane deta hai
def admin_only(current_user: model.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Sirf admin ye kaam kar sakta hai")
    return current_user

@app.get("/")
def home():
    return {"message": "SkyGuard AI Backend chal raha hai!"}

# Register API — naya user add karna
@app.post("/api/auth/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Pehle check karo email pehle se to nahi
    existing = db.query(model.User).filter(model.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Password hash karo
    hashed = hash_password(user.password)

    # Naya user banao
    new_user = model.User(
        name=user.name,
        email=user.email,
        password_hash=hashed,
        role=user.role
    )
    db.add(new_user)       # database mein add
    db.commit()            # save (pakka) karo
    db.refresh(new_user)   # updated data wapas lo
    return new_user

# Login API - email/password check karke token dena
@app.post("/api/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # NOTE: form_data.username mein hum EMAIL daalenge
    user = db.query(model.User).filter(model.User.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Galat email ya password")
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Galat email ya password")
    token = create_access_token({"user_id": user.id, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}

# Protected: sirf logged-in user apni info dekh sakta hai
@app.get("/api/users/me", response_model=schemas.UserResponse)
def my_info(current_user: model.User = Depends(get_current_user)):
    return current_user

# Admin only: sirf admin saare users ki list dekh sake
@app.get("/api/users", response_model=list[schemas.UserResponse])
def all_users(db: Session = Depends(get_db), admin: model.User = Depends(admin_only)):
    return db.query(model.User).all()


# Telemetry save karna (drone ya simulator ye bhejega)
# Telemetry save karna + live broadcast
@app.post("/api/telemetry", response_model=schemas.TelemetryResponse)
async def add_telemetry(
    data: schemas.TelemetryCreate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    # 1) Telemetry save karo
    new_data = model.Telemetry(
        drone_id=data.drone_id,
        pos_x=data.pos_x,
        pos_y=data.pos_y,
        pos_z=data.pos_z,
        altitude=data.altitude,
        speed=data.speed,
        battery=data.battery,
    )
    db.add(new_data)
    db.commit()
    db.refresh(new_data)

    # 2) Live telemetry broadcast
    await manager.broadcast({
        "type": "telemetry",
        "drone_id": new_data.drone_id,
        "pos_x": new_data.pos_x,
        "pos_y": new_data.pos_y,
        "altitude": new_data.altitude,
        "battery": new_data.battery,
    })

    # 3) Check: ye position kisi mamnu zone ke andar to nahi?
    zones = db.query(model.Geofence).filter(model.Geofence.is_active == 1).all()
    for z in zones:
        inside = (z.min_x <= new_data.pos_x <= z.max_x) and (z.min_y <= new_data.pos_y <= z.max_y)
        if inside:
            # Alert banao aur save karo
            alert = model.Alert(
                drone_id=new_data.drone_id,
                zone_name=z.name,
                message=f"ALERT! {new_data.drone_id} ne mamnu zone '{z.name}' cross kiya!",
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)

            # Live alert broadcast
            await manager.broadcast({
                "type": "alert",
                "drone_id": alert.drone_id,
                "zone_name": alert.zone_name,
                "message": alert.message,
            })

    return new_data

# Kisi drone ki saari telemetry history dekhna
@app.get("/api/drones/{drone_id}/telemetry", response_model=list[schemas.TelemetryResponse])
def get_telemetry(
    drone_id: str,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(get_current_user),
):
    records = (
        db.query(model.Telemetry)
        .filter(model.Telemetry.drone_id == drone_id)
        .order_by(model.Telemetry.created_at.desc())
        .all()
    )
    return records

# Live telemetry ke liye WebSocket (dashboard isse connect karega)
@app.websocket("/ws/telemetry")
async def ws_telemetry(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        
        # Naya geo-fence zone banana (sirf admin)
@app.post("/api/geofences", response_model=schemas.GeofenceResponse)
def create_geofence(
    data: schemas.GeofenceCreate,
    db: Session = Depends(get_db),
    admin: model.User = Depends(admin_only),
):
    zone = model.Geofence(
        name=data.name,
        min_x=data.min_x,
        min_y=data.min_y,
        max_x=data.max_x,
        max_y=data.max_y,
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone

# Saare zones dekhna
@app.get("/api/geofences", response_model=list[schemas.GeofenceResponse])
def list_geofences(db: Session = Depends(get_db), current_user: model.User = Depends(get_current_user)):
    return db.query(model.Geofence).all()

# Saare alerts dekhna
@app.get("/api/alerts", response_model=list[schemas.AlertResponse])
def list_alerts(db: Session = Depends(get_db), current_user: model.User = Depends(get_current_user)):
    return db.query(model.Alert).order_by(model.Alert.created_at.desc()).all()