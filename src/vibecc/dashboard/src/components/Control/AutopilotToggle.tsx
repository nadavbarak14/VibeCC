import { useState } from "react";
import type { AutopilotStatus } from "../../types/api";
import { Button } from "../common/Button";

interface AutopilotToggleProps {
  status?: AutopilotStatus;
  onStart: () => void;
  onStop: () => void;
  isLoading: boolean;
}

export function AutopilotToggle({
  status,
  onStart,
  onStop,
  isLoading,
}: AutopilotToggleProps) {
  const [confirmStop, setConfirmStop] = useState(false);
  const isRunning = status?.running ?? false;

  const handleStopClick = () => {
    if (confirmStop) {
      onStop();
      setConfirmStop(false);
    } else {
      setConfirmStop(true);
    }
  };

  const handleBlur = () => {
    setConfirmStop(false);
  };

  if (isRunning) {
    return (
      <Button
        data-testid="autopilot-toggle"
        variant="secondary"
        onClick={handleStopClick}
        onBlur={handleBlur}
        disabled={isLoading}
      >
        {isLoading ? "Stopping..." : confirmStop ? "Confirm Stop?" : "Stop"}
      </Button>
    );
  }

  return (
    <Button
      data-testid="autopilot-toggle"
      variant="primary"
      onClick={onStart}
      disabled={isLoading}
    >
      {isLoading ? "Starting..." : "Start"}
    </Button>
  );
}
