# Agent Tools

This directory contains tools that can be used by agents to perform various tasks.

## Available Tools

### Internet Search Tool

The Internet Search tool allows agents to search the internet for information.

### Bedrock Agent Tool

The Bedrock Agent tool allows agents to interact with Amazon Bedrock Agents.

### Word Document Tool

The Word Document tool allows agents to convert text content to a Microsoft Word document for download.

#### Usage

To use the Word Document tool, provide the following input:

```json
{
  "content": "The text content to be converted to a Word document.",
  "title": "Optional title for the document",
  "filename": "Optional filename for the document (without extension)"
}
```

The tool will return a Word document (.docx) that can be downloaded by the user.

#### Example

```python
from app.agents.tools.word_document import WordDocumentInput, create_word_document

input_data = WordDocumentInput(
    content="This is the content of my document.\nIt can have multiple paragraphs.",
    title="My Document",
    filename="my_document"
)

result = create_word_document(input_data, None, None)
# result will be a DocumentToolResult containing the Word document as a base64-encoded string
```

## Adding New Tools

To add a new tool:

1. Create a new Python file in this directory.
2. Define a Pydantic model for the tool input.
3. Implement a function to perform the tool's task.
4. Create an `AgentTool` instance for the tool.
5. Register the tool in `app/agents/utils.py`.