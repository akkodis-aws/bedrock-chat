"""
Word Document Tool

This tool converts text content to a Microsoft Word document (.docx) format.
It allows users to download LLM-generated content as a properly formatted Word document.
"""

import io
import logging
from typing import Dict, Union

from docx import Document
from pydantic import BaseModel, Field

from app.agents.tools.agent_tool import AgentTool
from app.repositories.models.conversation import DocumentToolResultModel
from app.repositories.models.custom_bot import BotModel
from app.routes.schemas.conversation import type_model_name

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WordDocumentInput(BaseModel):
    """Input schema for the word document tool."""
    content: str = Field(
        description="Text content to be converted to a Word document. Markdown formatting is supported."
    )
    title: str = Field(
        default="Generated Document",
        description="Title for the document. Will be used as the filename and as a heading in the document."
    )


def create_word_document(
    arg: WordDocumentInput, bot: BotModel | None, model: type_model_name | None
) -> Union[DocumentToolResultModel, Dict[str, str]]:
    """
    Convert text content to a Word document.
    
    Args:
        arg: Input containing the text content and optional title
        bot: Bot model (not used in this tool)
        model: Model name (not used in this tool)
        
    Returns:
        DocumentToolResultModel: A document tool result containing the Word document
        or Dict with error message if conversion fails
    """
    try:
        # Create a new Word document
        doc = Document()
        
        # Add title as heading
        doc.add_heading(arg.title, level=1)
        
        # Process content - split by newlines to handle paragraphs
        paragraphs = arg.content.split('\n')
        for para in paragraphs:
            if para.strip():  # Skip empty paragraphs
                doc.add_paragraph(para)
        
        # Save document to a bytes buffer
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        # Get the document as bytes
        doc_bytes = buffer.getvalue()
        
        # Create a safe filename (replace spaces with underscores)
        safe_filename = arg.title.replace(' ', '_')
        
        # Return as DocumentToolResultModel
        return DocumentToolResultModel(
            format="docx",
            name=f"{safe_filename}.docx",
            document=doc_bytes
        )
    
    except Exception as e:
        logger.error(f"Error creating Word document: {e}")
        return {
            "error": f"Failed to create Word document: {str(e)}"
        }


word_document_tool = AgentTool(
    name="create_word_document",
    description="Convert text content to a Microsoft Word document (.docx) that can be downloaded",
    args_schema=WordDocumentInput,
    function=create_word_document,
)