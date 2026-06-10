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

    def get_clean_signal(self) -> list[float]:
        """
        Método auxiliar: Pega a string de dados brutos e converte 
        em uma lista de números decimais para facilitar cálculos matemáticos.
        """
        raw_string = self.component[0].valueSampledData.data
        # Divide a string pelos espaços e converte cada pedaço em float
        return [float(x) for x in raw_string.strip().split()]

    def get_period_ms(self) -> float:
        return self.component[0].valueSampledData.period
    
class EcgResponse(BaseModel):
    status: str
    dispositivo: str
    periodo_ms: float
    total_pontos: int
    tamanho_string_prompt: int