import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function App() {
  const [health, setHealth] = useState("checking");
  const [topology, setTopology] = useState({ routers: [], links: [] });
  const [topologyStatus, setTopologyStatus] = useState("loading");

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
      })
      .catch(() => setTopologyStatus("error"));
  }, []);

  const routerPositions = buildRouterPositions(topology.routers);

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
              <article key={router.id}>
                <strong>Roteador {router.id}</strong>
                <span>
                  {router.ip}:{router.port}
                </span>
              </article>
            ))}
          </div>
        </aside>
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
