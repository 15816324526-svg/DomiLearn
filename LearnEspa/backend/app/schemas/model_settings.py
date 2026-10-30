from pydantic import BaseModel, Field


class ModelSettingsTestRequest(BaseModel):
    model_id: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=500)
    api_key: str = Field(min_length=1, max_length=1000)
