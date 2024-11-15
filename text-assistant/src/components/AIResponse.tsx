// src/components/AIResponse.tsx
import React from 'react';

interface AIResponseProps {
  aiResponse: string;
  responsePosition: { top: number; left: number };
  showResponse: boolean;
  setShowResponse: (show: boolean) => void;
  loading: boolean;
  onSave: (response: string) => void; // New prop for saving the response
}

const AIResponse: React.FC<AIResponseProps> = ({
  aiResponse,
  responsePosition,
  showResponse,
  setShowResponse,
  loading,
  onSave, // Destructure the new prop
}) => {
  if (!showResponse) return null;

  return (
    <div
      className="absolute bg-white border p-4 rounded-lg shadow-lg z-10 max-w-md max-h-64 overflow-auto"
      style={{ top: responsePosition.top, left: responsePosition.left }}
    >
      <div className="flex justify-between items-center mb-2">
        <span className="font-bold text-primary">AI Response</span>
        <button onClick={() => setShowResponse(false)} className="text-red-500 hover:text-red-700">
          &#x2715; {/* Unicode for close icon */}
        </button>
      </div>
      {loading ? (
        <div className="flex items-center justify-center h-full">
          <div className="loader ease-linear rounded-full border-4 border-t-4 border-gray-200 h-8 w-8"></div>
        </div>
      ) : (
        <div className="mb-2 text-textSecondary">{aiResponse}</div>
      )}
      {!loading && (
        <div className="flex space-x-2">
          <button
            onClick={() => navigator.clipboard.writeText(aiResponse)}
            className="mt-2 px-2 py-1 bg-primary text-white rounded hover:bg-accent"
          >
            Copy
          </button>
          <button
            onClick={() => {
              onSave(aiResponse); // Save the response
              setShowResponse(false); // Close the floating component
            }}
            className="mt-2 px-2 py-1 bg-secondary text-white rounded hover:bg-accent"
          >
            Save
          </button>
        </div>
      )}
    </div>
  );
};

export default AIResponse;
