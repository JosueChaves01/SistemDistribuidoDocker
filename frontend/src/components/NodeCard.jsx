const formatBytes = (bytes) => {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return (bytes / Math.pow(k, i)).toFixed(2) + " " + sizes[i];
};

const NodeCard = ({ name, info }) => {
  return (
    <div className="card" style={{
      border: "1px solid #ccc",
      borderRadius: "8px",
      padding: "1rem",
      margin: "0.5rem",
      width: "250px",
      boxShadow: "0 2px 5px rgba(0,0,0,0.1)"
    }}>
      <h3>{name}</h3>
      <p><strong>CPU:</strong> {parseFloat(info.cpu).toFixed(1)}%</p>
      <p><strong>RAM:</strong> {info.ram}%</p>
      <p><strong>Red:</strong> {formatBytes(info.net)}</p>
      <p><strong>IP:</strong> {info.ip}</p>
      <p><strong>Estado:</strong> {info.status || "desconocido"}</p>
      <p><strong>Tarea actual:</strong> {info.task_id || "ninguna"}</p>
    </div>
  );
};

export default NodeCard;
