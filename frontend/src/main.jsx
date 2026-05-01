import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function App() {
  const [health, setHealth] = useState("checking");
  const [topology, setTopology] = useState({ routers: [], links: [] });
  const [topologyStatus, setTopologyStatus] = useState("loading");
  const [selectedRouterId, setSelectedRouterId] = useState(null);
  const [routingTable, setRoutingTable] = useState({ router_id: null, routes: {} });
  const [routesStatus, setRoutesStatus] = useState("idle");
  const [messageForm, setMessageForm] = useState({
    source: "",
    destination: "",
    message: "",
    rdt_version: "1.0",
  });
  const [sendStatus, setSendStatus] = useState("");
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    fetch(`${apiBaseUrl}/health`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Health check failed");
        }
        return response.json();
      })
      .then((data) => setHealth(data.status))
      .catch(() => setHealth("offline"));

    fetch(`${apiBaseUrl}/topology`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Topology request failed");
        }
        return response.json();
      })
      .then((data) => {
        setTopology(data);
        setTopologyStatus("ready");
        setSelectedRouterId(data.routers[0]?.id ?? null);
        setMessageForm((current) => ({
          ...current,
          source: data.routers[0]?.id ? String(data.routers[0].id) : "",
          destination: data.routers[1]?.id ? String(data.routers[1].id) : "",
        }));
      })
      .catch(() => setTopologyStatus("error"));
  }, []);

  useEffect(() => {
    if (selectedRouterId === null) {
      return;
    }

    setRoutesStatus("loading");
    fetch(`${apiBaseUrl}/routes/${selectedRouterId}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Routes request failed");
        }
        return response.json();
      })
      .then((data) => {
        setRoutingTable(data);
        setRoutesStatus("ready");
      })
      .catch(() => setRoutesStatus("error"));
  }, [selectedRouterId]);

  useEffect(() => {
    if (selectedRouterId === null) {
      return;
    }

    fetch(`${apiBaseUrl}/logs/${selectedRouterId}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Logs request failed");
        }
        return response.json();
      })
      .then((data) => setLogs(data.lines))
      .catch(() => setLogs([]));
  }, [selectedRouterId, sendStatus]);

  const routerPositions = buildRouterPositions(topology.routers);

  function updateMessageForm(event) {
    const { name, value } = event.target;
    setMessageForm((current) => ({ ...current, [name]: value }));
  }

  function submitMessage(event) {
    event.preventDefault();
    setSendStatus("Enviando...");

    fetch(`${apiBaseUrl}/messages/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source: Number(messageForm.source),
        destination: Number(messageForm.destination),
        message: messageForm.message,
        rdt_version: messageForm.rdt_version,
      }),
    })
      .then((response) =>
        response.json().then((data) => {
          if (!response.ok) {
            throw new Error(data.detail ?? "Falha no envio");
          }
          return data;
        }),
      )
      .then((data) => {
        setSendStatus(`Enfileirada seq=${data.seq} rota=${data.path.join(" -> ")}`);
        setTimeout(() => setSendStatus((current) => `${current} `), 250);
      })
      .catch((error) => setSendStatus(error.message));
  }

  return (
    <main className="app-shell">
      <header className="top-bar">
        <div>
          <p className="eyebrow">Mensageria P2P Confiável</p>
          <h1>RDT P2P Visualizer</h1>
        </div>
        <span className={`status-badge status-${health}`}>
          API {health}
        </span>
      </header>

      <section className="workspace">
        <div className="panel network-panel">
          <div className="panel-header">
            <h2>Rede</h2>
            <span>Fase 2</span>
          </div>
          <NetworkGraph
            links={topology.links}
            positions={routerPositions}
            status={topologyStatus}
          />
        </div>

        <aside className="panel details-panel">
          <h2>Topologia</h2>
          <dl>
            <div>
              <dt>Roteadores</dt>
              <dd>{topology.routers.length}</dd>
            </div>
            <div>
              <dt>Enlaces</dt>
              <dd>{topology.links.length}</dd>
            </div>
            <div>
              <dt>Configuração</dt>
              <dd>roteador.config + enlaces.config</dd>
            </div>
          </dl>

          <div className="router-list" aria-label="Roteadores configurados">
            {topology.routers.map((router) => (
              <button
                className={router.id === selectedRouterId ? "selected-router" : ""}
                key={router.id}
                onClick={() => setSelectedRouterId(router.id)}
                type="button"
              >
                <strong>Roteador {router.id}</strong>
                <span>
                  {router.ip}:{router.port}
                </span>
              </button>
            ))}
          </div>
        </aside>
      </section>

      <section className="routes-section">
        <div className="panel send-panel">
          <div className="panel-header">
            <h2>Enviar Mensagem</h2>
            <span>UDP básico</span>
          </div>
          <form className="message-form" onSubmit={submitMessage}>
            <label>
              Origem
              <select name="source" value={messageForm.source} onChange={updateMessageForm}>
                {topology.routers.map((router) => (
                  <option key={router.id} value={router.id}>
                    Roteador {router.id}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Destino
              <select name="destination" value={messageForm.destination} onChange={updateMessageForm}>
                {topology.routers.map((router) => (
                  <option key={router.id} value={router.id}>
                    Roteador {router.id}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Protocolo
              <select name="rdt_version" value={messageForm.rdt_version} onChange={updateMessageForm}>
                <option value="1.0">RDT 1.0</option>
                <option value="2.0">RDT 2.0</option>
                <option value="3.0">RDT 3.0</option>
              </select>
            </label>
            <label className="message-field">
              Mensagem
              <input
                maxLength="100"
                name="message"
                onChange={updateMessageForm}
                required
                value={messageForm.message}
              />
            </label>
            <button type="submit">Enviar</button>
          </form>
          {sendStatus && <p className="send-status">{sendStatus}</p>}
        </div>

        <div className="panel routes-panel">
          <div className="panel-header">
            <h2>Tabela de Rotas</h2>
            <span>
              {selectedRouterId === null ? "Sem roteador" : `Roteador ${selectedRouterId}`}
            </span>
          </div>
          <RoutingTable table={routingTable} status={routesStatus} />
        </div>

        <div className="panel logs-panel">
          <div className="panel-header">
            <h2>Logs</h2>
            <span>{selectedRouterId === null ? "Sem roteador" : `Roteador ${selectedRouterId}`}</span>
          </div>
          <pre className="log-output">
            {logs.length ? logs.join("\n") : "Sem logs para este roteador."}
          </pre>
        </div>
      </section>
    </main>
  );
}

function NetworkGraph({ links, positions, status }) {
  if (status === "loading") {
    return <div className="network-state">Carregando topologia...</div>;
  }

  if (status === "error") {
    return <div className="network-state network-error">Falha ao carregar topologia</div>;
  }

  const routers = Object.values(positions);

  return (
    <div className="network-graph" aria-label="Topologia carregada">
      <svg viewBox="0 0 100 100" role="img" aria-label="Enlaces da rede">
        {links.map((link) => {
          const source = positions[link.source];
          const target = positions[link.target];

          if (!source || !target) {
            return null;
          }

          return (
            <g key={`${link.source}-${link.target}`}>
              <line x1={source.x} y1={source.y} x2={target.x} y2={target.y} />
              <text x={(source.x + target.x) / 2} y={(source.y + target.y) / 2}>
                {link.cost}
              </text>
            </g>
          );
        })}
      </svg>

      {routers.map((router) => (
        <div
          className="router-node"
          key={router.id}
          style={{ left: `${router.x}%`, top: `${router.y}%` }}
        >
          {router.id}
        </div>
      ))}
    </div>
  );
}

function RoutingTable({ table, status }) {
  if (status === "idle" || status === "loading") {
    return <div className="table-state">Carregando rotas...</div>;
  }

  if (status === "error") {
    return <div className="table-state table-error">Falha ao carregar rotas</div>;
  }

  const routes = Object.entries(table.routes);

  if (routes.length === 0) {
    return <div className="table-state">Nenhuma rota calculada</div>;
  }

  return (
    <div className="routes-table-wrap">
      <table className="routes-table">
        <thead>
          <tr>
            <th>Destino</th>
            <th>Próximo salto</th>
            <th>Custo</th>
            <th>Caminho</th>
          </tr>
        </thead>
        <tbody>
          {routes.map(([destination, route]) => (
            <tr key={destination}>
              <td>{destination}</td>
              <td>{route.next_hop}</td>
              <td>{route.cost}</td>
              <td>{route.path.join(" -> ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function buildRouterPositions(routers) {
  const sortedRouters = [...routers].sort((first, second) => first.id - second.id);
  const centerX = 50;
  const centerY = 50;
  const radius = 34;

  return sortedRouters.reduce((positions, router, index) => {
    const angle = (Math.PI * 2 * index) / sortedRouters.length - Math.PI / 2;
    positions[router.id] = {
      id: router.id,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
    return positions;
  }, {});
}

createRoot(document.getElementById("root")).render(<App />);
