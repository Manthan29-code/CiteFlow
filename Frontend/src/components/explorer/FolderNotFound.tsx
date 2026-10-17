import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/common/Button';

export const FolderNotFound: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center py-24 px-4 text-center">
      <div className="w-16 h-16 rounded-2xl bg-red-50 border border-red-200 flex items-center justify-center text-red-600 mb-4 shadow-sm">
        <AlertCircle className="w-8 h-8" />
      </div>
      <h3 className="font-serif text-2xl font-bold text-charcoal-900 mb-2">
        Folder Not Found
      </h3>
      <p className="text-sm text-charcoal/60 font-sans max-w-md mb-6">
        This folder may have been moved, deleted, or you do not have permission to access it.
      </p>
      <Button
        variant="primary"
        onClick={() => navigate('/')}
        className="gap-2"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Return to Root Library</span>
      </Button>
    </div>
  );
};
