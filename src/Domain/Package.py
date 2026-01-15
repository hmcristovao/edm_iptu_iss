from src.Domain.Parameters import Parameters
import pandas as pd

class Package():
    def __init__(self,parameters: Parameters ,data: pd.DataFrame = None):
        self.parameters = parameters
        self.datas = data
