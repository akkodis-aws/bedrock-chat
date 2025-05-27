import React, { useCallback } from 'react';
import ButtonIcon from './ButtonIcon';
import { BaseProps } from '../@types/common';
import { PiDownload } from 'react-icons/pi';

interface WindowWithFileSaveAPI {
  showSaveFilePicker?: (options?: {
    suggestedName?: string;
    types?: Array<{
      description: string;
      accept: Record<string, string[]>;
    }>;
  }) => Promise<FileSystemFileHandle>;
}

type Props = BaseProps & {
  documentData: string; // Base64 encoded document data
  fileName: string;
  mimeType: string;
};

const ButtonDownloadDocument: React.FC<Props> = (props) => {
  const downloadDocument = useCallback(async () => {
    try {
      // Convert base64 to binary
      const binaryString = window.atob(props.documentData);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      
      // Create blob from binary data
      const blob = new Blob([bytes], { type: props.mimeType });
      
      // Modern browsers - Using File System Access API
      const savePicker = (window as Window & WindowWithFileSaveAPI).showSaveFilePicker;
      if (savePicker) {
        try {
          const handle = await savePicker({
            suggestedName: props.fileName,
            types: [{
              description: 'Document',
              accept: {
                [props.mimeType]: [`.${props.fileName.split('.').pop()}`]
              }
            }]
          });
          const writable = await handle.createWritable();
          await writable.write(blob);
          await writable.close();
          return;
        } catch (err: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
          // User cancelled the save dialog or other error
          if (err.name !== 'AbortError') {
            console.error('Failed to save document:', err);
          }
          return;
        }
      }

      // Fallback for older browsers
      const downloadLink = document.createElement('a');
      downloadLink.download = props.fileName;
      downloadLink.href = window.URL.createObjectURL(blob);
      downloadLink.click();
      window.URL.revokeObjectURL(downloadLink.href);

    } catch (error) {
      console.error('Failed to download document:', error);
    }
  }, [props.documentData, props.fileName, props.mimeType]);

  return (
    <ButtonIcon
      className={props.className}
      onClick={downloadDocument}
      title="Download document"
    >
      <PiDownload />
    </ButtonIcon>
  );
};

export default ButtonDownloadDocument;