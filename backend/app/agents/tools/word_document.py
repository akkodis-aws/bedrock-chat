"""
Word Document Tool

This module provides a tool for converting text content to a Word document.
It allows users to download the LLM-generated content as a Word document.
"""

import io
import base64
from typing import Optional

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from mypy_boto3_bedrock_runtime.literals import DocumentFormatType

from app.agents.tools.agent_tool import AgentTool
from app.repositories.models.custom_bot import BotModel
from app.routes.schemas.conversation import DocumentToolResult, type_model_name
from pydantic import BaseModel, Field


class WordDocumentInput(BaseModel):
    """
    Input schema for the word document tool.
    
    Attributes:
        content: The text content to be converted to a Word document.
        title: Optional title for the Word document.
        filename: Optional filename for the Word document (without extension).
    """
    content: str = Field(description="The text content to be converted to a Word document.")
    title: Optional[str] = Field(
        default=None, 
        description="Optional title for the Word document. If provided, it will be added as a heading."
    )
    filename: Optional[str] = Field(
        default="document", 
        description="Optional filename for the Word document (without extension)."
    )


def create_word_document(
    arg: WordDocumentInput, bot: BotModel | None, model: type_model_name | None
) -> DocumentToolResult:
    """
    Creates a Word document from the provided text content.
    
    Args:
        arg: The input containing the text content and optional title and filename.
        bot: The bot model (not used in this function).
        model: The model name (not used in this function).
        
    Returns:
        A DocumentToolResult containing the Word document as a base64-encoded string.
    """
    # Create a new Word document
    doc = Document()
    
    # Add title if provided
    if arg.title:
        title = doc.add_heading(arg.title, level=1)
        title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    
    # Add content paragraphs
    for paragraph_text in arg.content.split('\n'):
        if paragraph_text.strip():  # Skip empty paragraphs
            paragraph = doc.add_paragraph(paragraph_text)
            paragraph.style.font.size = Pt(11)  # Standard font size
    
    # Save the document to a bytes buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    # Get the bytes and encode as base64
    doc_bytes = buffer.getvalue()
    doc_base64 = base64.b64encode(doc_bytes)
    
    # Determine filename
    filename = arg.filename if arg.filename else "document"
    
    # Return the document as a DocumentToolResult
    return DocumentToolResult(
        format="docx",
        name=f"{filename}.docx",
        document=doc_base64,
    )


word_document_tool = AgentTool(
    name="create_word_document",
    description="Convert text content to a Microsoft Word document for download",
    args_schema=WordDocumentInput,
    function=create_word_document,
)