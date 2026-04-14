// frontend/src/components/FileUpload.js
import React, { useState, useRef } from 'react';
import { uploadFile } from '../services/api';
import { formatBytes } from '../utils/formatters';
import './FileUpload.css';

const FileUpload = ({ onUploaded }) => {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const fileInputRef = useRef();

  const handleFile = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const result = await uploadFile(file);
      setUploadResult(result);
      if (onUploaded) onUploaded(result);
    } catch (err) {
      console.error('Upload failed:', err);
      setUploadResult({ error: err.response?.data?.detail || 'Upload failed' });
    }
    setUploading(false);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  };

  return (
    <div className="glass-card file-upload fade-in" style={{ animationDelay: '0.1s' }}>
      <div className="section-title">
        <span className="icon">📁</span> File Upload
      </div>

      <div
        className={`drop-zone ${dragging ? 'drag-active' : ''} ${uploading ? 'uploading' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,video/*"
          hidden
          onChange={(e) => handleFile(e.target.files[0])}
        />
        {uploading ? (
          <div className="upload-spinner" />
        ) : (
          <>
            <div className="drop-icon">⬆️</div>
            <p className="drop-text">Drop an image/video here or click to browse</p>
            <p className="drop-hint">JPG, PNG, MP4, AVI — up to 500 MB</p>
          </>
        )}
      </div>

      {uploadResult && !uploadResult.error && (
        <div className="upload-meta">
          <div className="meta-item"><span>Type:</span> <strong>{uploadResult.file_type}</strong></div>
          <div className="meta-item"><span>Resolution:</span> <strong>{uploadResult.resolution[0]} × {uploadResult.resolution[1]}</strong></div>
          <div className="meta-item"><span>Frames:</span> <strong>{uploadResult.frames}</strong></div>
          <div className="meta-item"><span>Size:</span> <strong>{formatBytes(uploadResult.size_mb)}</strong></div>
        </div>
      )}
      {uploadResult?.error && (
        <p className="error-text">❌ {uploadResult.error}</p>
      )}
    </div>
  );
};

export default FileUpload;
