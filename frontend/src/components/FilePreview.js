// frontend/src/components/FilePreview.js
import React, { useState, useEffect, useRef } from 'react';
import './FilePreview.css';

const FilePreview = ({ file }) => {
  const [previewUrl, setPreviewUrl] = useState(null);
  const [videoFrames, setVideoFrames] = useState([]);
  const videoRef = useRef(null);

  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    setVideoFrames([]);

    return () => {
      URL.revokeObjectURL(url);
      videoFrames.forEach(f => URL.revokeObjectURL(f));
    };
  }, [file]); // eslint-disable-line react-hooks/exhaustive-deps

  const extractFrames = (videoEl) => {
    if (!videoEl) return;
    const canvas = document.createElement('canvas');
    canvas.width = videoEl.videoWidth;
    canvas.height = videoEl.videoHeight;
    const ctx = canvas.getContext('2d');
    const dur = videoEl.duration;
    const times = [0.1, dur * 0.33, dur * 0.66].filter(t => t < dur);
    const frames = [];
    let idx = 0;

    const capture = () => {
      ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(blob => {
        if (blob) frames.push(URL.createObjectURL(blob));
        idx++;
        if (idx < times.length) {
          videoEl.currentTime = times[idx];
        } else {
          setVideoFrames(frames);
          videoEl.currentTime = 0;
        }
      }, 'image/jpeg', 0.85);
    };

    videoEl.onseeked = capture;
    videoEl.currentTime = times[0];
  };

  if (!file || !previewUrl) return null;

  const isVideo = file.type?.startsWith('video');

  return (
    <div className="file-preview">
      <div className="preview-label">Preview</div>
      {isVideo ? (
        <>
          <video
            ref={videoRef}
            src={previewUrl}
            className="preview-media preview-video"
            controls
            muted
            onLoadedMetadata={(e) => extractFrames(e.target)}
          />
          {videoFrames.length > 0 && (
            <div className="frame-strip">
              {videoFrames.map((f, i) => (
                <img key={i} src={f} alt={`Frame ${i + 1}`} className="frame-thumb" />
              ))}
            </div>
          )}
        </>
      ) : (
        <img src={previewUrl} alt="Preview" className="preview-media preview-image" />
      )}
    </div>
  );
};

export default FilePreview;
