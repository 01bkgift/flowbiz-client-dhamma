"""
คลาสพื้นฐานสำหรับ AI Agents ทั้งหมดในระบบ
ใช้ Generic Type เพื่อรองรับ Input/Output ที่แตกต่างกันในแต่ละ Agent
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

# Type variables สำหรับ Input และ Output models
InputModel = TypeVar('InputModel', bound=BaseModel)
OutputModel = TypeVar('OutputModel', bound=BaseModel)


class BaseAgent(ABC, Generic[InputModel, OutputModel]):
    """
    คลาสพื้นฐานสำหรับ AI Agents ทั้งหมด
    
    Attributes:
        name: ชื่อของ Agent
        version: เวอร์ชันของ Agent
        description: คำอธิบาย Agent
    """

    def __init__(self, name: str, version: str = "1.0.0", description: str = ""):
        self.name = name
        self.version = version
        self.description = description

    @abstractmethod
    def run(self, input_data: InputModel) -> OutputModel:
        """
        ฟังก์ชันหลักสำหรับประมวลผลข้อมูลของ Agent
        
        Args:
            input_data: ข้อมูลนำเข้าตาม schema ของ Agent
            
        Returns:
            ผลลัพธ์ตาม schema ของ Agent
            
        Raises:
            NotImplementedError: ต้อง override ใน subclass
        """
        raise NotImplementedError("Subclass ต้อง implement method run()")

    def get_info(self) -> dict:
        """ข้อมูลพื้นฐานของ Agent"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "type": self.__class__.__name__
        }

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', version='{self.version}')"
