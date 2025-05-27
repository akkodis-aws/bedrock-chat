import sys
import base64
import unittest
from io import BytesIO

sys.path.append(".")

from app.agents.tools.word_document import WordDocumentInput, create_word_document, word_document_tool
from app.agents.utils import get_available_tools
from docx import Document


class TestWordDocumentTool(unittest.TestCase):
    def test_create_word_document_basic(self):
        """Test creating a basic Word document with just content."""
        input_data = WordDocumentInput(
            content="This is a test document.\nIt has multiple paragraphs.\n\nIncluding some with extra line breaks.",
            filename="test_doc"
        )
        
        result = create_word_document(input_data, None, "claude-v3.5-sonnet-v2")
        
        # Check that the result has the expected format and name
        self.assertEqual(result.format, "docx")
        self.assertEqual(result.name, "test_doc.docx")
        
        # Check that the document is a valid base64-encoded docx file
        doc_bytes = base64.b64decode(result.document)
        self.assertTrue(len(doc_bytes) > 0)
        
        # Try to open the document to verify it's valid
        doc_buffer = BytesIO(doc_bytes)
        doc = Document(doc_buffer)
        
        # Check that the document has the expected content
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        self.assertEqual(len(paragraphs), 3)
        self.assertEqual(paragraphs[0], "This is a test document.")
        self.assertEqual(paragraphs[1], "It has multiple paragraphs.")
        self.assertEqual(paragraphs[2], "Including some with extra line breaks.")

    def test_create_word_document_with_title(self):
        """Test creating a Word document with a title."""
        input_data = WordDocumentInput(
            content="This is the content of the document.",
            title="Test Document Title",
            filename="test_with_title"
        )
        
        result = create_word_document(input_data, None, "claude-v3.5-sonnet-v2")
        
        # Check that the result has the expected format and name
        self.assertEqual(result.format, "docx")
        self.assertEqual(result.name, "test_with_title.docx")
        
        # Check that the document is a valid base64-encoded docx file
        doc_bytes = base64.b64decode(result.document)
        doc_buffer = BytesIO(doc_bytes)
        doc = Document(doc_buffer)
        
        # Check that the document has the title and content
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        self.assertEqual(len(paragraphs), 2)
        self.assertEqual(paragraphs[0], "Test Document Title")
        self.assertEqual(paragraphs[1], "This is the content of the document.")

    def test_default_filename(self):
        """Test that a default filename is used when none is provided."""
        input_data = WordDocumentInput(
            content="Content only, no filename specified."
        )
        
        result = create_word_document(input_data, None, "claude-v3.5-sonnet-v2")
        
        # Check that the default filename is used
        self.assertEqual(result.name, "document.docx")

    def test_tool_registration(self):
        """Test that the word_document_tool is properly registered."""
        tools = get_available_tools()
        tool_names = [tool.name for tool in tools]
        
        # Check that the word_document_tool is in the list of available tools
        self.assertIn("create_word_document", tool_names)
        
        # Find the word_document_tool in the list
        word_tool = next((tool for tool in tools if tool.name == "create_word_document"), None)
        self.assertIsNotNone(word_tool)
        
        # Check that it has the correct description and args_schema
        self.assertEqual(word_tool.description, "Convert text content to a Microsoft Word document for download")
        self.assertEqual(word_tool.args_schema, WordDocumentInput)


if __name__ == "__main__":
    unittest.main()