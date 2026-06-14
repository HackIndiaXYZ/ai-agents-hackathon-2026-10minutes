// components/FeedbackButtons.jsx
import React, { useState } from "react";
import { submitFeedback } from "../api/client";

const FeedbackButtons = ({ sessionId, turnNumber, onRated }) => {
  const [rating, setRating] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleRate = async (value) => {
    if (rating || loading) return;
    setLoading(true);
    try {
      await submitFeedback({ sessionId, turnNumber, rating: value });
      setRating(value);
      onRated && onRated(value);
    } catch (e) {
      console.error("Feedback error", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "8px" }}>
      <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Was this helpful?</span>
      {["helpful", "not_helpful"].map((val) => {
        const isSelected = rating === val;
        const isHelpful = val === "helpful";
        return (
          <button
            key={val}
            id={`feedback-${val}-${turnNumber}`}
            onClick={() => handleRate(val)}
            disabled={!!rating || loading}
            title={isHelpful ? "Helpful" : "Not helpful"}
            style={{
              background: isSelected
                ? isHelpful ? "var(--green-dim)" : "var(--red-dim)"
                : "transparent",
              border: `1px solid ${isSelected
                ? isHelpful ? "var(--green)" : "var(--red)"
                : "var(--border-subtle)"}`,
              borderRadius: "6px",
              padding: "3px 8px",
              cursor: rating ? "default" : "pointer",
              fontSize: "15px",
              opacity: rating && !isSelected ? 0.3 : 1,
              transition: "all 0.2s",
            }}
          >
            {isHelpful ? "👍" : "👎"}
          </button>
        );
      })}
      {rating && (
        <span style={{ fontSize: "11px", color: "var(--text-muted)", marginLeft: "4px" }}>
          Thanks!
        </span>
      )}
    </div>
  );
};

export default FeedbackButtons;
