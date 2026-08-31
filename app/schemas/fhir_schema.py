from pydantic import BaseModel
from typing import List

class Origin(BaseModel):
    value: float

class ValueSampledData(BaseModel):
    origin: Origin
    period: float
    factor: float
    lowerLimit: float
    upperLimit: float
    dimensions: int
    data: str

class Component(BaseModel):
    valueSampledData: ValueSampledData

class Device(BaseModel):
    display: str

class FHIRObservation(BaseModel):
    resourceType: str
    status: str
    device: Device
    component: List[Component]
    
    # Metodo para obter os sinais limpos a partir dos dados utilizando o fator e a origem para ajustar os valores brutos e retornar uma lista de valores float
    def get_clean_signal(self) -> list[float]:
        raw_string = self.component[0].valueSampledData.data
        raw_values = [float(x) for x in raw_string.strip().split()]
    
        factor = self.component[0].valueSampledData.factor
        origin = self.component[0].valueSampledData.origin.value
    
        return [(v * factor) + origin for v in raw_values]

    def get_period_ms(self) -> float:
        return self.component[0].valueSampledData.period
    
class EcgResponse(BaseModel):
    status: str
    dispositivo: str
    periodo_ms: float
    total_pontos: int
    tamanho_string_prompt: int