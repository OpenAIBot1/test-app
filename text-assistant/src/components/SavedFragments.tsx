// src/components/SavedFragments.tsx
import React from 'react';

interface SavedFragmentsProps {
  fragments: string[];
  onCopy: (fragment: string) => void;
}

const SavedFragments: React.FC<SavedFragmentsProps> = ({ fragments, onCopy }) => {
  return (
    <div className="w-1/4 pl-4">
      <div className="bg-gray-100 p-4 rounded-lg shadow-md">
        <h2 className="text-lg font-bold mb-4 text-primary">Saved Fragments</h2>
        <div className="flex flex-col space-y-4">
          {fragments.map((fragment, index) => (
            <div key={index} className="bg-white p-4 rounded-lg shadow-sm">
              <span className="text-textSecondary font-medium block mb-2">{fragment}</span>
              <button
                onClick={() => onCopy(fragment)}
                className="w-full px-2 py-1 bg-primary text-white rounded hover:bg-accent"
              >
                Copy
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SavedFragments;
