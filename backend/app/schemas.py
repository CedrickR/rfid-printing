from datetime import datetime
from pydantic import BaseModel
from pydantic import ConfigDict

class LoginRequest(BaseModel):
    username: str
    password: str



class ImportResponse(BaseModel):

    id: int
    filename: str

    imported_by: str
    imported_at: datetime

    total_rows: int
    active_assets: int
    excluded_assets: int            

    model_config = ConfigDict(
        from_attributes=True
    )




class CreatePrintJobRequest(BaseModel):
    asset_ids: list[int]