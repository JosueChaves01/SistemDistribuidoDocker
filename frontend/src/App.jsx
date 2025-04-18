import { useEffect, useState } from "react";
import NodeCard from "./components/NodeCard";

function App() {
  const [nodes, setNodes] = useState({});
  const [queueSize, setQueueSize] = useState("Cargando...");
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);

  const fetchStatus = async () => {
    try {
      const apiBase = "http://localhost:8000";
      
      const [nodesRes, queueRes] = await Promise.all([
        fetch(`${apiBase}/workers`),
        fetch(`${apiBase}/queue_size`)
      ]);

      // Verificar errores HTTP
      if (!nodesRes.ok) throw new Error(`Error workers: ${nodesRes.status}`);
      if (!queueRes.ok) throw new Error(`Error queue: ${queueRes.status}`);

      const [nodesData, queueData] = await Promise.all([
        nodesRes.json(),
        queueRes.json()
      ]);

      setNodes(nodesData);
      setQueueSize(queueData.pending_tasks);
      setError(null);
    } catch (err) {
      console.error("Fetch error:", err);
      setError("Error obteniendo datos del sistema");
      setQueueSize("Error");
    }
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return alert("Selecciona una imagen");

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("http://localhost:8000/upload", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();

    if (data.status === "sent") {
      alert("Tarea enviada.");
    } else {
      alert("Error al enviar tarea: " + (data.message || "sin detalle"));
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 300);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ padding: "2rem" }}>
      <h1>Sistema Distribuido</h1>
      
      {error && (
        <div style={{ color: "red", margin: "1rem 0" }}>
          ⚠️ {error}
        </div>
      )}

      <h3>📦 Tareas en cola: {typeof queueSize === "number" ? queueSize : queueSize}</h3>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        {Object.entries(nodes).map(([name, info]) => (
          <NodeCard key={name} name={name} info={info} />
        ))}
      </div>

      <hr />

      <h2>Subir imagen para procesar</h2>
      <input type="file" onChange={handleFileChange} />
      <button onClick={handleUpload}>Enviar imagen</button>
    </div>
  );
}

export default App;