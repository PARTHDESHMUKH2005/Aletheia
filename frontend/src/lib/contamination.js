// Contamination level from what the model reported: a purity category plus a list of visible contaminants.
// Deliberately no percentage: the backend validates none (see backend/app/tools/assessment.py).
export function contaminationLevel(item) {
  const contaminants = item?.contaminants || [];
  if (!item || item.purity === "unknown") {
    return { level: 0, tone: "unknown", label: "Not assessed", note: "The photo did not allow a purity call.", contaminants };
  }
  if (item.purity === "mixed" && contaminants.length >= 2) {
    return { level: 3, tone: "high", label: "High", note: "Mixed material with several visible contaminants.", contaminants };
  }
  if (item.purity === "mixed" || contaminants.length) {
    return { level: 2, tone: "moderate", label: "Moderate", note: "Some visible contamination or mixed material.", contaminants };
  }
  return { level: 1, tone: "low", label: "Low", note: "Looks clean: high purity, no visible contaminants.", contaminants };
}
