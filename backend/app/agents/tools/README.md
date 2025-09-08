# Agent Tools

This directory contains tools that can be used by agents to perform various tasks.

## Available Tools

### Internet Search Tool
The Internet Search Tool allows agents to search the internet for information.

### Word Document Tool
The Word Document Tool converts text content to a Microsoft Word document (.docx) format that can be downloaded by users.

#### Usage
To use the Word Document Tool, provide the following parameters:
- `content`: The text content to be converted to a Word document
- `title` (optional): The title for the document (defaults to "Generated Document")

#### Example
```
I need to create a Word document with the following content:

Title: Project Proposal
Content: 
This is a project proposal for implementing a new feature.

The feature will include:
- Component A
- Component B
- Component C

Timeline: 3 months
```

The tool will generate a properly formatted Word document that can be downloaded by the user.

## Adding New Tools
To add a new tool:
1. Create a new Python file in this directory
2. Define an input schema using Pydantic
3. Implement the tool function
4. Create an AgentTool instance
5. Register the tool in `app/agents/utils.py`