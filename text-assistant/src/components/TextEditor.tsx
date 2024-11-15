// src/components/TextEditor.tsx
import React, { useMemo, useCallback, useState } from 'react';
import { createEditor, BaseEditor, Descendant, Transforms } from 'slate';
import { Slate, Editable, withReact, ReactEditor, RenderElementProps } from 'slate-react';
import axios from 'axios';
import ActionPanel from './ActionPanel';
import AIResponse from './AIResponse';
import SavedFragments from './SavedFragments'; // Importing the SavedFragments component

// Custom Types for Slate
type CustomText = { text: string };

type ParagraphElement = { type: 'paragraph'; children: CustomText[] };
type CustomElement = ParagraphElement;

declare module 'slate' {
  interface CustomTypes {
    Editor: BaseEditor & ReactEditor;
    Element: CustomElement;
    Text: CustomText;
  }
}

const TextEditor: React.FC = () => {
  const editor = useMemo(() => withReact(createEditor()), []);

  const initialValue: Descendant[] = useMemo(
    () => [
      {
        type: 'paragraph',
        children: [{ text: '' }],
      } as CustomElement,
    ],
    []
  );

  const [selectedAction, setSelectedAction] = useState('translate');
  const [aiResponse, setAiResponse] = useState('');
  const [responsePosition, setResponsePosition] = useState({ top: 0, left: 0 });
  const [showResponse, setShowResponse] = useState(false);
  const [loading, setLoading] = useState(false);
  const [savedFragments, setSavedFragments] = useState<string[]>([]); // State for saved fragments

  const renderElement = useCallback((props: RenderElementProps) => {
    return <p {...props.attributes}>{props.children}</p>;
  }, []);

  const handleSelection = useCallback(() => {
    const selection = window.getSelection();
    if (selection && selection.toString()) {
      const selectedText = selection.toString();
      const range = selection.getRangeAt(0).getBoundingClientRect();
      setResponsePosition({ top: range.bottom + window.scrollY, left: range.left + window.scrollX });
      processText(selectedText);
      setShowResponse(true);
    } else {
      setShowResponse(false);
    }
  }, [selectedAction]);

  const processText = async (text: string) => {
    setLoading(true);
    try {
      const response = await axios.post(
        'https://openrouter.ai/api/v1/chat/completions',
        {
          messages: [{ role: 'user', content: generatePrompt(text) }],
          model: 'meta-llama/llama-3.2-11b-vision-instruct:free',
        },
        {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${process.env.REACT_APP_OPENROUTER_API_KEY}`,
          },
        }
      );
      console.log('API Response:', response.data);
      setAiResponse(response.data.choices[0].message.content);
    } catch (error) {
      console.error('Error sending request:', error);
    } finally {
      setLoading(false);
    }
  };

  const generatePrompt = (text: string) => {
    switch (selectedAction) {
      case 'translate':
        return `Translate the following text to English:\n\n${text}. Output only the translation, no other text`;
      case 'explain':
        return `Explain the following text in simple terms:\n\n${text}, Output only the explanation, no other text`;
      case 'summarize':
        return `Summarize the following text in 1-2 sentences:\n\n${text}. Output only the summary, no other text`;
      default:
        return text;
    }
  };

  const handleChange = useCallback(() => {
    // If you need to access the content, you can use editor.children
    // const content = JSON.stringify(editor.children);
    // Perform any necessary actions
  }, [editor]);

  const handleReset = () => {
    Transforms.select(editor, { path: [0, 0], offset: 0 });
    Transforms.removeNodes(editor, { at: [0] });
    Transforms.insertNodes(editor, initialValue);
  };

  const handleSave = (response: string) => {
    setSavedFragments((prevFragments) => [...prevFragments, response]);
  };

  return (
    <div className="relative bg-background min-h-screen p-8 font-sans text-textPrimary flex">
      {/* Side Panel for Preset Actions */}
      <ActionPanel selectedAction={selectedAction} setSelectedAction={setSelectedAction} />

      {/* Text Editor */}
      <div className="w-3/4 border border-gray-300 p-6 rounded-lg shadow-lg bg-white relative">
        <Slate editor={editor} initialValue={initialValue} onChange={handleChange}>
          <Editable
            renderElement={renderElement}
            onSelect={handleSelection}
            placeholder="Paste your text here..."
            className="focus:outline-none text-textSecondary"
          />
        </Slate>
        <button
          onClick={handleReset}
          className="mt-4 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
        >
          Reset
        </button>
      </div>

      {/* AI Response Floating Window */}
      <AIResponse
        aiResponse={aiResponse}
        responsePosition={responsePosition}
        showResponse={showResponse}
        setShowResponse={setShowResponse}
        loading={loading}
        onSave={handleSave} // Pass the handleSave function
      />

      {/* Saved Fragments */}
      <SavedFragments fragments={savedFragments} onCopy={(fragment) => navigator.clipboard.writeText(fragment)} />
    </div>
  );
};

export default TextEditor;
