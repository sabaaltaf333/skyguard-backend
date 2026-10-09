from pydantic import BaseModel, EmailStr

# Jab naya user register karega to ye data aayega
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "operator"

# Jab user ki info wapas bhejenge (password ke baghair)
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True
        
        # Login ke waqt ye data aayega
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Login kamyab hone par token aise wapas aayega
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
    # Jab drone ka data andar aayega to ye shakal hogi
class TelemetryCreate(BaseModel):
    drone_id: str
    pos_x: float
    pos_y: float
    pos_z: float
    altitude: float
    speed: float
    battery: float

# Jab data wapas bhejenge to ye shakal hogi
class TelemetryResponse(BaseModel):
    id: int
    drone_id: str
    pos_x: float
    pos_y: float
    pos_z: float
    altitude: float
    speed: float
    battery: float

    class Config:
        from_attributes = True
        
        # Zone banane ke liye input
class GeofenceCreate(BaseModel):
    name: str
    min_x: float
    min_y: float
    max_x: float
    max_y: float

# Zone wapas bhejne ke liye
class GeofenceResponse(BaseModel):
    id: int
    name: str
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    is_active: int

    class Config:
        from_attributes = True

# Alert wapas bhejne ke liye
class AlertResponse(BaseModel):
    id: int
    drone_id: str
    zone_name: str
    message: str

    class Config:
        from_attributes = True