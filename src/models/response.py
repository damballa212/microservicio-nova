"""
Modelos de respuesta formateada.

Define la estructura de las respuestas del chatbot después de fragmentación.
"""

from pydantic import BaseModel, Field, field_validator


class FormattedResponse(BaseModel):
    """
    Respuesta formateada y fragmentada para WhatsApp.

    Las respuestas largas se dividen en hasta 3 partes para
    simular una conversación más natural.

    Attributes:
        part_1: Primera parte (siempre requerida)
        part_2: Segunda parte (opcional)
        part_3: Tercera parte (opcional)
    """

    part_1: str = Field(description="Primera parte de la respuesta (siempre requerida)")
    part_2: str = Field(default="", description="Segunda parte de la respuesta (opcional)")
    part_3: str = Field(default="", description="Tercera parte de la respuesta (opcional)")

    @field_validator("part_1")
    @classmethod
    def part_1_not_empty(cls, v: str) -> str:
        """Valida que part_1 no esté vacío."""
        if not v or not v.strip():
            raise ValueError("part_1 no puede estar vacío")
        return v.strip()

    @field_validator("part_2", "part_3")
    @classmethod
    def clean_optional_parts(cls, v: str) -> str:
        """Limpia las partes opcionales."""
        return v.strip() if v else ""

    def to_parts_list(self) -> list[str]:
        """
        Convierte a una lista de partes no vacías.

        Returns:
            Lista con solo las partes que tienen contenido
        """
        parts = [self.part_1]
        if self.part_2:
            parts.append(self.part_2)
        if self.part_3:
            parts.append(self.part_3)
        return parts

    @property
    def total_parts(self) -> int:
        """Número total de partes con contenido."""
        return len(self.to_parts_list())

    @property
    def total_length(self) -> int:
        """Longitud total de todas las partes."""
        return sum(len(p) for p in self.to_parts_list())


class ClassificationResult(BaseModel):
    """
    Resultado de la clasificación de escalamiento.

    Attributes:
        needs_escalation: Si requiere atención humana
        confidence: Nivel de confianza (0-1)
        reason: Razón del resultado
    """

    needs_escalation: bool = Field(description="Si la conversación requiere atención humana")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Nivel de confianza de la clasificación"
    )
    reason: str | None = Field(default=None, description="Razón de la clasificación")
