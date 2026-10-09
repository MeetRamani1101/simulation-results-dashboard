import { useState } from "react";
import { componentImageUrl } from "../api/client";

/**
 * Renders a component's optional reference photo. Not every component has
 * one (the backend 404s when none was found alongside its source data), so
 * this quietly renders nothing rather than a broken-image icon.
 */
export default function ComponentImage({ componentId, alt, style }) {
  const [failed, setFailed] = useState(false);
  if (failed) return null;
  return (
    <img
      src={componentImageUrl(componentId)}
      alt={alt}
      style={style}
      onError={() => setFailed(true)}
    />
  );
}
