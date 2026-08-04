import { useState, useEffect, useRef, useCallback } from 'react';
import type { FC } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, FilePlus, Loader2 } from 'lucide-react';
import { apiClient } from '../services/api';
import './Documents.css';

interface Document {
  id: string;
  title: string;
  file_name: string;
  status: string;
  created_at: string;
  chunk_count?: number;
  error_message?: string;
}

export const Documents: FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDragActive, setIsDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocuments = useCallback(async (background = false) => {
    if (!background) setIsLoading(true);
    try {
      const data = await apiClient.get<Document[]>('/api/v1/documents/');
      setDocuments(data);
    } catch (err) {
      console.error('Failed to fetch documents', err);
      if (!background) setError('Failed to load documents.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Intelligent polling: only poll if there are documents still uploading/processing
  useEffect(() => {
    const pendingDocs = documents.some(
      (doc) => doc.status === 'uploading' || doc.status === 'processing'
    );

    if (pendingDocs) {
      const interval = setInterval(() => fetchDocuments(true), 2500);
      return () => clearInterval(interval);
    }
  }, [documents, fetchDocuments]);

  const handleFile = async (file: File) => {
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setUploadProgress(10); // Fake immediate progress

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', file.name);

    try {
      // Fake progress for UX
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => (prev >= 90 ? 90 : prev + 10));
      }, 300);

      await apiClient.upload('/api/v1/documents/', formData);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      // Give the 100% state a moment to render before refreshing
      setTimeout(() => {
        setUploadProgress(0);
        setIsUploading(false);
        fetchDocuments(true);
      }, 500);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(true);
  };

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
      e.dataTransfer.clearData();
    }
  };

  const getStatusDisplay = (status: string, errMsg?: string) => {
    switch (status.toLowerCase()) {
      case 'ready': 
        return (
          <span className="status-badge status-ready">
            <CheckCircle2 size={14} /> Ready
          </span>
        );
      case 'failed': 
        return (
          <span className="status-badge status-failed" title={errMsg}>
            <AlertCircle size={14} /> Failed
          </span>
        );
      case 'uploading':
      case 'processing':
      default: 
        return (
          <span className="status-badge status-processing">
            <Loader2 size={14} className="spin" /> Processing
          </span>
        );
    }
  };

  return (
    <div className="documents-page animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Knowledge Base</h1>
          <p className="page-subtitle">Upload and manage documents for AI retrieval context.</p>
        </div>
      </div>

      <div 
        className={`upload-dropzone card ${isDragActive ? 'drag-active' : ''} ${isUploading ? 'uploading' : ''}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
      >
        <div className="upload-content">
          {isUploading ? (
            <div className="upload-progress-container">
              <Loader2 size={40} className="upload-icon spin text-primary" />
              <h3>Uploading Document...</h3>
              <div className="progress-bar-wrapper">
                <div className="progress-bar" style={{ width: `${uploadProgress}%` }}></div>
              </div>
              <p className="upload-hint">{uploadProgress}% complete</p>
            </div>
          ) : (
            <>
              <div className="upload-icon-wrapper">
                <UploadCloud size={32} className="text-primary" />
              </div>
              <h3>Click or drag file to this area to upload</h3>
              <p className="upload-hint">Support for PDF, DOCX, TXT, and Markdown files.</p>
            </>
          )}
          
          <input
            type="file"
            ref={fileInputRef}
            className="hidden-input"
            accept=".pdf,.docx,.txt,.md"
            onChange={(e) => {
              if (e.target.files?.[0]) handleFile(e.target.files[0]);
              e.target.value = ''; // Reset input
            }}
            disabled={isUploading}
          />
        </div>
      </div>

      {error && (
        <div className="error-banner animate-fade-in">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="documents-container card mt-6">
        <div className="card-header">
          <h2>Indexed Documents</h2>
          <span className="document-count">{documents.length} files</span>
        </div>
        
        {isLoading && documents.length === 0 ? (
          <div className="skeleton-container">
            {[1, 2, 3].map(i => <div key={i} className="skeleton-row"></div>)}
          </div>
        ) : documents.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">
              <FilePlus size={32} className="text-muted" />
            </div>
            <h3>No documents found</h3>
            <p className="text-muted">Upload your first document above to start building your knowledge base.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Chunks</th>
                  <th>Date Added</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td>
                      <div className="doc-title-cell">
                        <FileText size={16} className="text-muted" />
                        <span className="font-medium truncate" title={doc.title}>{doc.title}</span>
                      </div>
                    </td>
                    <td>{getStatusDisplay(doc.status, doc.error_message)}</td>
                    <td className="text-muted">{doc.chunk_count ?? '-'}</td>
                    <td className="text-muted text-sm">
                      {new Date(doc.created_at).toLocaleDateString(undefined, { 
                        year: 'numeric', month: 'short', day: 'numeric', 
                        hour: '2-digit', minute: '2-digit'
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
