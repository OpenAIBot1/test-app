// src/components/ActionPanel.tsx
import React from 'react';

interface ActionPanelProps {
  selectedAction: string;
  setSelectedAction: (action: string) => void;
}

const ActionPanel: React.FC<ActionPanelProps> = ({ selectedAction, setSelectedAction }) => {
  return (
    <div className="w-1/4 pr-4">
      <div className="bg-white p-4 rounded-lg shadow-md">
        <h2 className="text-lg font-bold mb-4">Actions</h2>
        <div className="flex flex-col space-y-2">
          {['translate', 'explain', 'summarize'].map((action) => (
            <button
              key={action}
              onClick={() => setSelectedAction(action)}
              className={`px-4 py-2 rounded-lg transition-colors duration-200 shadow-md ${
                selectedAction === action ? 'bg-primary text-white' : 'bg-secondary text-white hover:bg-accent'
              }`}
            >
              {action.charAt(0).toUpperCase() + action.slice(1)}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ActionPanel;
