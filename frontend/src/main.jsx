import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8045";
const wsBaseUrl = apiBaseUrl.replace(/^http/, "ws");
const LAYOUT_OPTIONS = ["spring", "random", "circular", "shell"];

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
  const [simulationSettings, setSimulationSettings] = useState({
    loss_rate: 0.1,
    corruption_rate: 0.1,
    timeout_seconds: 2,
    max_retries: 5,
  });
  const [settingsForm, setSettingsForm] = useState({
    lossPercent: "10",
    corruptionPercent: "10",
    timeout_seconds: "2",
    max_retries: "5",
  });
  const [settingsStatus, setSettingsStatus] = useState("");
  const [topologyForm, setTopologyForm] = useState({
    selectedLink: "",
    editCost: "",
  });
  const [randomGraphForm, setRandomGraphForm] = useState({
    nodes: "5",
    edges: "6",
    min_cost: "1",
    max_cost: "20",
    layout: "spring",
    connected: true,
  });
  const [layoutForm, setLayoutForm] = useState({ layout: "spring" });
  const [topologyActionStatus, setTopologyActionStatus] = useState("");
  const [sendStatus, setSendStatus] = useState("");
  const [logs, setLogs] = useState([]);
  const [events, setEvents] = useState([]);
  const [eventsConnection, setEventsConnection] = useState("connecting");
  const [animationState, setAnimationState] = useState({
    activePackets: [],
    activeEdges: [],
    highlightedRouters: [],
    transientEffects: [],
  });
  const animationTimers = useRef([]);
  const selectedRouterRef = useRef(null);

  useEffect(() => {
    selectedRouterRef.current = selectedRouterId;
  }, [selectedRouterId]);

  useEffect(() => {
    fetch(`${apiBaseUrl}/health`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Health check failed");
        }
        return response.json();
      })
      .then((data) => {
        setHealth(data.status);
        loadTopology();
        loadSimulationSettings();
      })
      .catch(() => {
        setHealth("offline");
        setTopologyStatus("error");
      });
  }, []);

  function loadTopology() {
    return fetch(`${apiBaseUrl}/topology`)
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
        setRandomGraphForm((current) => ({
          ...current,
          nodes: String(data.routers.length || 5),
          edges: String(data.links.length || 6),
          layout: data.layout ?? current.layout,
        }));
        setLayoutForm({ layout: data.layout ?? "spring" });
        setMessageForm((current) => ({
          ...current,
          source: data.routers[0]?.id ? String(data.routers[0].id) : "",
          destination: data.routers[1]?.id ? String(data.routers[1].id) : "",
        }));
      })
      .catch(() => setTopologyStatus("error"));
  }

  function loadSimulationSettings() {
    return fetch(`${apiBaseUrl}/simulation/settings`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Settings request failed");
        }
        return response.json();
      })
      .then((data) => {
        setSimulationSettings(data);
        setSettingsForm(settingsToForm(data));
      })
      .catch(() => setSettingsStatus("Falha ao carregar configurações."));
  }

  useEffect(() => {
    let active = true;
    let socket;

    fetch(`${apiBaseUrl}/events`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Events request failed");
        }
        return response.json();
      })
      .then((data) => {
        if (active) {
          setEvents(data);
        }
      })
      .catch(() => {
        if (active) {
          setEvents([]);
        }
      });

    try {
      socket = new WebSocket(`${wsBaseUrl}/ws/events`);
    } catch (_error) {
      setEventsConnection("offline");
      return () => {
        active = false;
      };
    }

    socket.addEventListener("open", () => setEventsConnection("live"));
    socket.addEventListener("close", () => setEventsConnection("offline"));
    socket.addEventListener("error", () => setEventsConnection("offline"));
    socket.addEventListener("message", (messageEvent) => {
      const event = JSON.parse(messageEvent.data);
      if (event.type === "HEARTBEAT") {
        return;
      }

      setEvents((current) => appendUniqueEvent(current, event));
      if (event.type === "SIMULATION_SETTINGS_UPDATED") {
        const nextSettings = {
          loss_rate: event.loss_rate,
          corruption_rate: event.corruption_rate,
          timeout_seconds: event.timeout_seconds,
          max_retries: event.max_retries,
        };
        setSimulationSettings(nextSettings);
        setSettingsForm(settingsToForm(nextSettings));
      }
      if (event.type === "TOPOLOGY_UPDATED" && event.topology) {
        setTopology(event.topology);
        setLayoutForm({ layout: event.topology.layout ?? "spring" });
        if (selectedRouterRef.current !== null) {
          loadRoutesForRouter(selectedRouterRef.current);
        }
      }
      applyNetworkEvent(event, setAnimationState, animationTimers);
    });

    return () => {
      active = false;
      clearAnimationTimers(animationTimers);
      socket.close();
    };
  }, []);

  function loadSelectedLogs() {
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
  }

  useEffect(() => {
    if (selectedRouterId === null) {
      return;
    }

    loadRoutesForRouter(selectedRouterId);
  }, [selectedRouterId]);

  useEffect(() => {
    if (!topology.links.length) {
      setTopologyForm((current) => ({
        ...current,
        selectedLink: "",
        editCost: "",
      }));
      return;
    }

    setTopologyForm((current) => {
      const selectedLinkExists = topology.links.some((link) => linkKey(link) === current.selectedLink);
      const selectedLink = selectedLinkExists ? current.selectedLink : linkKey(topology.links[0]);
      const link = topology.links.find((item) => linkKey(item) === selectedLink);

      return {
        ...current,
        selectedLink,
        editCost: link ? String(link.cost) : current.editCost,
      };
    });
  }, [topology.links, topology.routers]);

  useEffect(() => {
    setRandomGraphForm((current) => ({
      ...current,
      nodes: String(topology.routers.length || current.nodes),
      edges: String(topology.links.length || current.edges),
    }));
  }, [topology.routers.length, topology.links.length]);

  function loadRoutesForRouter(routerId) {
    setRoutesStatus("loading");
    return fetch(`${apiBaseUrl}/routes/${routerId}`)
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
  }

  useEffect(() => {
    if (selectedRouterId === null) {
      return;
    }

    loadSelectedLogs();
  }, [selectedRouterId, events.length]);

  const routerPositions = buildRouterPositions(topology.routers);
  const networkState = getLatestNetworkState(events);

  function updateMessageForm(event) {
    const { name, value } = event.target;
    setMessageForm((current) => ({ ...current, [name]: value }));
  }

  function updateSettingsForm(event) {
    const { name, value } = event.target;
    setSettingsForm((current) => ({ ...current, [name]: value }));
  }

  function submitSettings(event) {
    event.preventDefault();
    setSettingsStatus("Salvando configurações...");

    fetch(`${apiBaseUrl}/simulation/settings`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        loss_rate: Number(settingsForm.lossPercent) / 100,
        corruption_rate: Number(settingsForm.corruptionPercent) / 100,
        timeout_seconds: Number(settingsForm.timeout_seconds),
        max_retries: Number(settingsForm.max_retries),
      }),
    })
      .then((response) =>
        response.json().then((data) => {
          if (!response.ok) {
            throw new Error(data.detail ?? "Falha ao salvar configurações");
          }
          return data;
        }),
      )
      .then((data) => {
        setSimulationSettings(data);
        setSettingsForm(settingsToForm(data));
        setSettingsStatus("Configurações atualizadas.");
      })
      .catch((error) => setSettingsStatus(error.message));
  }

  function updateTopologyForm(event) {
    const { name, value } = event.target;
    setTopologyForm((current) => {
      if (name === "selectedLink") {
        const link = topology.links.find((item) => linkKey(item) === value);
        return {
          ...current,
          selectedLink: value,
          editCost: link ? String(link.cost) : current.editCost,
        };
      }
      return { ...current, [name]: value };
    });
  }

  function updateRandomGraphForm(event) {
    const { checked, name, type, value } = event.target;
    setRandomGraphForm((current) => ({ ...current, [name]: type === "checkbox" ? checked : value }));
  }

  function updateLayoutForm(event) {
    const { name, value } = event.target;
    setLayoutForm((current) => ({ ...current, [name]: value }));
  }

  function submitLinkCost(event) {
    event.preventDefault();
    const selectedLink = parseLinkKey(topologyForm.selectedLink);
    if (!selectedLink) {
      setTopologyActionStatus("Selecione um enlace para alterar.");
      return;
    }

    submitTopologyAction("PATCH", {
      source: selectedLink.source,
      target: selectedLink.target,
      cost: Number(topologyForm.editCost),
    });
  }

  function submitTopologyAction(method, payload) {
    setTopologyActionStatus("Atualizando topologia...");
    fetch(`${apiBaseUrl}/topology/links`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then((response) =>
        response.json().then((data) => {
          if (!response.ok) {
            throw new Error(data.detail ?? "Falha ao atualizar topologia");
          }
          return data;
        }),
      )
      .then((data) => {
        setTopology(data);
        loadTopology();
        if (selectedRouterId !== null) {
          loadRoutesForRouter(selectedRouterId);
        }
        setTopologyActionStatus("As rotas foram recalculadas com Dijkstra.");
      })
      .catch((error) => setTopologyActionStatus(error.message));
  }

  function submitRandomGraph(event) {
    event.preventDefault();
    setTopologyActionStatus("Gerando grafo random com NetworkX...");
    fetch(`${apiBaseUrl}/topology/random`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nodes: Number(randomGraphForm.nodes),
        edges: Number(randomGraphForm.edges),
        min_cost: Number(randomGraphForm.min_cost),
        max_cost: Number(randomGraphForm.max_cost),
        layout: randomGraphForm.layout,
        connected: randomGraphForm.connected,
      }),
    })
      .then((response) =>
        response.json().then((data) => {
          if (!response.ok) {
            throw new Error(data.detail ?? "Falha ao gerar grafo random");
          }
          return data;
        }),
      )
      .then((data) => {
        setTopology(data);
        if (selectedRouterId !== null) {
          loadRoutesForRouter(selectedRouterId);
        }
        setTopologyActionStatus("Grafo random gerado e rotas recalculadas.");
      })
      .catch((error) => setTopologyActionStatus(error.message));
  }

  function submitLayout(event) {
    event.preventDefault();
    setTopologyActionStatus("Aplicando layout no backend...");
    fetch(`${apiBaseUrl}/topology/layout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ layout: layoutForm.layout }),
    })
      .then((response) =>
        response.json().then((data) => {
          if (!response.ok) {
            throw new Error(data.detail ?? "Falha ao aplicar layout");
          }
          return data;
        }),
      )
      .then((data) => {
        setTopology(data);
        setTopologyActionStatus(`Layout ${data.layout} aplicado.`);
      })
      .catch((error) => setTopologyActionStatus(error.message));
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
            <span>Fase 8</span>
          </div>
          <NetworkGraph
            activeLink={networkState.activeLink}
            activeRouterId={networkState.activeRouterId}
            animationState={animationState}
            links={topology.links}
            positions={routerPositions}
            status={topologyStatus}
            tone={networkState.tone}
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
              <dd>{topology.generated_by === "random" ? "NetworkX random" : "roteador.config + enlaces.config"}</dd>
            </div>
            <div>
              <dt>Layout</dt>
              <dd>{topology.layout ?? "spring"}</dd>
            </div>
            <div>
              <dt>Conectado</dt>
              <dd>{topology.is_connected ? "Sim" : "Não"}</dd>
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
            <span>UDP + RDT</span>
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

        <div className="panel settings-panel">
          <div className="panel-header">
            <h2>Configurações da Simulação</h2>
            <span>
              Perda {formatPercent(simulationSettings.loss_rate)} · Corrupção {formatPercent(simulationSettings.corruption_rate)}
            </span>
          </div>
          <form className="control-form" onSubmit={submitSettings}>
            <label>
              Perda (%)
              <input
                max="100"
                min="0"
                name="lossPercent"
                onChange={updateSettingsForm}
                step="1"
                type="number"
                value={settingsForm.lossPercent}
              />
            </label>
            <label>
              Corrupção (%)
              <input
                max="100"
                min="0"
                name="corruptionPercent"
                onChange={updateSettingsForm}
                step="1"
                type="number"
                value={settingsForm.corruptionPercent}
              />
            </label>
            <label>
              Timeout (s)
              <input
                min="0.1"
                name="timeout_seconds"
                onChange={updateSettingsForm}
                step="0.1"
                type="number"
                value={settingsForm.timeout_seconds}
              />
            </label>
            <label>
              Tentativas
              <input
                min="1"
                name="max_retries"
                onChange={updateSettingsForm}
                step="1"
                type="number"
                value={settingsForm.max_retries}
              />
            </label>
            <button type="submit">Salvar</button>
          </form>
          {settingsStatus && <p className="send-status">{settingsStatus}</p>}
        </div>

        <div className="panel topology-editor-panel">
          <div className="panel-header">
            <h2>Gerar Grafo Random</h2>
            <span>NetworkX no backend</span>
          </div>
          <form className="control-form topology-control-form" onSubmit={submitRandomGraph}>
            <label>
              Nós
              <input
                min="5"
                name="nodes"
                onChange={updateRandomGraphForm}
                step="1"
                type="number"
                value={randomGraphForm.nodes}
              />
            </label>
            <label>
              Arestas
              <input
                min="0"
                name="edges"
                onChange={updateRandomGraphForm}
                step="1"
                type="number"
                value={randomGraphForm.edges}
              />
            </label>
            <label>
              Custo mín.
              <input
                min="1"
                name="min_cost"
                onChange={updateRandomGraphForm}
                step="1"
                type="number"
                value={randomGraphForm.min_cost}
              />
            </label>
            <label>
              Custo máx.
              <input
                min="1"
                name="max_cost"
                onChange={updateRandomGraphForm}
                step="1"
                type="number"
                value={randomGraphForm.max_cost}
              />
            </label>
            <label>
              Layout
              <select name="layout" value={randomGraphForm.layout} onChange={updateRandomGraphForm}>
                {LAYOUT_OPTIONS.map((layout) => (
                  <option key={layout} value={layout}>
                    {layout}
                  </option>
                ))}
              </select>
            </label>
            <label className="checkbox-field">
              <input
                checked={randomGraphForm.connected}
                name="connected"
                onChange={updateRandomGraphForm}
                type="checkbox"
              />
              Garantir conectado
            </label>
            <button type="submit">Gerar</button>
          </form>
          {topologyActionStatus && <p className="send-status">{topologyActionStatus}</p>}
        </div>

        <div className="panel topology-editor-panel">
          <div className="panel-header">
            <h2>Layout</h2>
            <span>Posições calculadas no backend</span>
          </div>
          <form className="control-form topology-control-form" onSubmit={submitLayout}>
            <label>
              Layout
              <select name="layout" value={layoutForm.layout} onChange={updateLayoutForm}>
                {LAYOUT_OPTIONS.map((layout) => (
                  <option key={layout} value={layout}>
                    {layout}
                  </option>
                ))}
              </select>
            </label>
            <button type="submit">Aplicar layout</button>
          </form>
        </div>

        <div className="panel topology-editor-panel">
          <div className="panel-header">
            <h2>Pesos</h2>
            <span>Dijkstra recalculado no backend</span>
          </div>
          <form className="control-form topology-control-form" onSubmit={submitLinkCost}>
            <label>
              Enlace
              <select name="selectedLink" value={topologyForm.selectedLink} onChange={updateTopologyForm}>
                {topology.links.map((link) => (
                  <option key={linkKey(link)} value={linkKey(link)}>
                    {link.source} ↔ {link.target}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Novo custo
              <input
                min="1"
                name="editCost"
                onChange={updateTopologyForm}
                step="1"
                type="number"
                value={topologyForm.editCost}
              />
            </label>
            <button type="submit">Alterar</button>
          </form>
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

        <div className="panel events-panel">
          <div className="panel-header">
            <h2>Timeline</h2>
            <span>{eventsConnection === "live" ? "WebSocket ativo" : "Eventos recentes"}</span>
          </div>
          <EventTimeline events={events} />
        </div>
      </section>
    </main>
  );
}

function appendUniqueEvent(current, event) {
  const key = eventKey(event);
  if (current.some((item) => eventKey(item) === key)) {
    return current;
  }
  return [...current, event].slice(-200);
}

function eventKey(event) {
  return `${event.timestamp}-${event.type}-${event.seq ?? ""}-${event.router_id ?? ""}-${event.line ?? ""}`;
}

function settingsToForm(settings) {
  return {
    lossPercent: String(Math.round(Number(settings.loss_rate) * 100)),
    corruptionPercent: String(Math.round(Number(settings.corruption_rate) * 100)),
    timeout_seconds: String(settings.timeout_seconds),
    max_retries: String(settings.max_retries),
  };
}

function formatPercent(value) {
  return `${Math.round(Number(value) * 100)}%`;
}

function linkKey(link) {
  return `${link.source}-${link.target}`;
}

function parseLinkKey(value) {
  const [source, target] = String(value).split("-").map(Number);
  if (!source || !target) {
    return null;
  }
  return { source, target };
}

function NetworkGraph({ activeLink, activeRouterId, animationState, links, positions, status, tone }) {
  if (status === "loading") {
    return <div className="network-state">Carregando topologia...</div>;
  }

  if (status === "error") {
    return <div className="network-state network-error">Falha ao carregar topologia</div>;
  }

  const routers = Object.values(positions);
  const normalizedLinks = links.map((link) => ({
    ...link,
    source: String(link.source),
    target: String(link.target),
  }));
  const graphEdges = normalizedLinks
    .map((link) => {
      const source = positions[link.source];
      const target = positions[link.target];

      if (!source || !target) {
        return null;
      }

      return buildGraphEdge(source, target, link, isActiveGraphLink(activeLink, animationState.activeEdges, link));
    })
    .filter(Boolean);
  const activeRouterKey = activeRouterId === null || activeRouterId === undefined ? null : String(activeRouterId);
  const highlightedRouters = new Set(animationState.highlightedRouters.map(String));

  return (
    <div className={`network-graph tone-${tone}`} aria-label="Topologia carregada">
      <svg preserveAspectRatio="none" viewBox="0 0 100 100" role="img" aria-label="Enlaces da rede">
        <g className="edge-layer">
          {graphEdges.map((edge) => (
            <line
              className={edge.isActive ? "active-link" : ""}
              key={`line-${edge.key}`}
              vectorEffect="non-scaling-stroke"
              x1={edge.x1}
              x2={edge.x2}
              y1={edge.y1}
              y2={edge.y2}
            />
          ))}
        </g>
        <g className="packet-layer">
          {animationState.activePackets.map((packet) => {
            const from = positions[String(packet.from)];
            const to = positions[String(packet.to)];

            if (!from || !to) {
              return null;
            }

            return (
              <g className={`packet packet-${packet.packetType.toLowerCase()}`} key={packet.id}>
                <circle r={packet.packetType === "DATA" ? "2.4" : "1.9"}>
                  <animateMotion
                    begin="0s"
                    dur={`${packet.duration}ms`}
                    fill="freeze"
                    path={`M ${from.x} ${from.y} L ${to.x} ${to.y}`}
                  />
                </circle>
                <text dy="-3.4">
                  <animateMotion
                    begin="0s"
                    dur={`${packet.duration}ms`}
                    fill="freeze"
                    path={`M ${from.x} ${from.y} L ${to.x} ${to.y}`}
                  />
                  {packet.packetType}
                  {packet.attempt > 1 ? ` #${packet.attempt}` : ""}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {graphEdges.map((edge) => (
        <span
          className="edge-label"
          key={`label-${edge.key}`}
          style={{ left: `${edge.labelX}%`, top: `${edge.labelY}%` }}
        >
          {edge.cost}
        </span>
      ))}

      {routers.map((router) => (
        <div
          className={`router-node ${router.id === activeRouterKey || highlightedRouters.has(router.id) ? "active-router" : ""}`}
          key={router.id}
          style={{ left: `${router.x}%`, top: `${router.y}%` }}
        >
          {router.id}
        </div>
      ))}

      {animationState.transientEffects.map((effect) => {
        const router = positions[String(effect.routerId)];

        if (!router) {
          return null;
        }

        return (
          <div
            className={`transient-effect effect-${effect.kind.toLowerCase()}`}
            key={effect.id}
            style={{ left: `${router.x}%`, top: `${router.y}%` }}
          >
            <span>{effect.symbol}</span>
          </div>
        );
      })}

      <div className="packet-legend" aria-label="Legenda de pacotes">
        <span><i className="legend-dot legend-data" /> DATA</span>
        <span><i className="legend-dot legend-ack" /> ACK</span>
        <span><i className="legend-dot legend-nak" /> NAK</span>
        <span><b>✕</b> DROP</span>
        <span><b>⚠</b> CORR</span>
        <span><b>⏱</b> TIMEOUT</span>
      </div>
    </div>
  );
}

function buildGraphEdge(source, target, link, isActive) {
  const midX = (source.x + target.x) / 2;
  const midY = (source.y + target.y) / 2;
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const length = Math.hypot(dx, dy) || 1;
  const labelOffset = 4;
  const label = String(link.cost);

  return {
    key: `${link.source}-${link.target}`,
    cost: label,
    isActive,
    labelX: midX + (-dy / length) * labelOffset,
    labelY: midY + (dx / length) * labelOffset,
    x1: source.x,
    x2: target.x,
    y1: source.y,
    y2: target.y,
  };
}

const ANIMATED_EVENT_TYPES = new Set([
  "MESSAGE_SENT",
  "MESSAGE_FORWARDED",
  "MESSAGE_RECEIVED",
  "PACKET_DROPPED",
  "PACKET_CORRUPTED",
  "ACK_SENT",
  "ACK_RECEIVED",
  "ACK_FORWARDED",
  "NAK_SENT",
  "NAK_RECEIVED",
  "NAK_FORWARDED",
  "TIMEOUT",
  "MESSAGE_RETRY",
  "MESSAGE_DELIVERED",
  "MESSAGE_FAILED",
]);

const PACKET_EVENT_TYPES = new Set([
  "MESSAGE_SENT",
  "MESSAGE_FORWARDED",
  "ACK_SENT",
  "ACK_FORWARDED",
  "NAK_SENT",
  "NAK_FORWARDED",
  "MESSAGE_RETRY",
]);

function applyNetworkEvent(event, setAnimationState, animationTimers) {
  if (!ANIMATED_EVENT_TYPES.has(event.type)) {
    return;
  }

  const routerId = getEventRouterId(event);
  const nextHop = getEventNextHop(event);
  const packetType = getEventPacketType(event);
  const now = Date.now();
  const highlightIds = compactIds([routerId, nextHop, event.source, event.destination]);
  const effect = buildTransientEffect(event, now);
  const shouldAnimatePacket = PACKET_EVENT_TYPES.has(event.type) && routerId !== null && nextHop !== null;
  const packet = shouldAnimatePacket
    ? {
        id: `${event.type}-${event.seq ?? "x"}-${routerId}-${nextHop}-${event.attempt ?? 1}-${now}`,
        seq: event.seq,
        from: routerId,
        to: nextHop,
        packetType,
        attempt: Number(event.attempt ?? 1),
        duration: 900,
      }
    : null;
  const activeEdge = shouldAnimatePacket
    ? {
        id: `${routerId}-${nextHop}-${now}`,
        source: routerId,
        target: nextHop,
      }
    : null;

  setAnimationState((current) => ({
    activePackets: packet ? [...current.activePackets, packet] : removePacketsForSeq(current.activePackets, event),
    activeEdges: activeEdge ? [...current.activeEdges, activeEdge] : current.activeEdges,
    highlightedRouters: mergeIds(current.highlightedRouters, highlightIds),
    transientEffects: effect ? [...current.transientEffects, effect] : current.transientEffects,
  }));

  if (packet) {
    scheduleAnimationUpdate(animationTimers, () => {
      setAnimationState((current) => ({
        ...current,
        activePackets: current.activePackets.filter((item) => item.id !== packet.id),
      }));
    }, packet.duration + 150);
  }

  if (activeEdge) {
    scheduleAnimationUpdate(animationTimers, () => {
      setAnimationState((current) => ({
        ...current,
        activeEdges: current.activeEdges.filter((item) => item.id !== activeEdge.id),
      }));
    }, 1300);
  }

  if (highlightIds.length) {
    scheduleAnimationUpdate(animationTimers, () => {
      setAnimationState((current) => ({
        ...current,
        highlightedRouters: current.highlightedRouters.filter((item) => !highlightIds.includes(String(item))),
      }));
    }, ["MESSAGE_DELIVERED", "MESSAGE_FAILED"].includes(event.type) ? 2200 : 1400);
  }

  if (effect) {
    scheduleAnimationUpdate(animationTimers, () => {
      setAnimationState((current) => ({
        ...current,
        transientEffects: current.transientEffects.filter((item) => item.id !== effect.id),
      }));
    }, effect.duration);
  }

  if (["PACKET_DROPPED", "MESSAGE_DELIVERED", "MESSAGE_FAILED"].includes(event.type)) {
    scheduleAnimationUpdate(animationTimers, () => {
      setAnimationState((current) => ({
        ...current,
        activePackets: removePacketsForSeq(current.activePackets, event),
      }));
    }, 250);
  }
}

function scheduleAnimationUpdate(animationTimers, callback, delay) {
  const timerId = window.setTimeout(() => {
    animationTimers.current = animationTimers.current.filter((item) => item !== timerId);
    callback();
  }, delay);
  animationTimers.current = [...animationTimers.current, timerId];
}

function clearAnimationTimers(animationTimers) {
  animationTimers.current.forEach((timerId) => window.clearTimeout(timerId));
  animationTimers.current = [];
}

function buildTransientEffect(event, now) {
  const routerId = getEventRouterId(event) ?? event.destination ?? event.source;
  const effectsByType = {
    MESSAGE_RECEIVED: { kind: "received", symbol: "●", duration: 1100 },
    PACKET_DROPPED: { kind: "drop", symbol: "✕", duration: 1500 },
    PACKET_CORRUPTED: { kind: "corrupted", symbol: "⚠", duration: 1500 },
    TIMEOUT: { kind: "timeout", symbol: "⏱", duration: 1700 },
    MESSAGE_RETRY: { kind: "retry", symbol: `#${event.attempt ?? 2}`, duration: 1400 },
    MESSAGE_DELIVERED: { kind: "delivered", symbol: "✓", duration: 1800 },
    MESSAGE_FAILED: { kind: "failed", symbol: "!", duration: 1800 },
  };
  const effect = effectsByType[event.type];

  if (!effect || routerId === null || routerId === undefined) {
    return null;
  }

  return {
    id: `${event.type}-${event.seq ?? "x"}-${routerId}-${now}`,
    routerId,
    ...effect,
  };
}

function getEventRouterId(event) {
  return normalizeRouterId(event.current_router ?? event.router_id);
}

function getEventNextHop(event) {
  const explicitNextHop = normalizeRouterId(event.next_hop);
  if (explicitNextHop !== null) {
    return explicitNextHop;
  }

  const routerId = getEventRouterId(event);
  if (routerId === null || !Array.isArray(event.path)) {
    return null;
  }

  const routerIndex = event.path.map(String).indexOf(String(routerId));
  if (routerIndex === -1 || routerIndex >= event.path.length - 1) {
    return null;
  }

  return normalizeRouterId(event.path[routerIndex + 1]);
}

function getEventPacketType(event) {
  if (event.packet_type) {
    return String(event.packet_type).toUpperCase();
  }
  if (event.type.startsWith("ACK")) {
    return "ACK";
  }
  if (event.type.startsWith("NAK")) {
    return "NAK";
  }
  return "DATA";
}

function normalizeRouterId(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  return String(value);
}

function compactIds(values) {
  return values.map(normalizeRouterId).filter((value) => value !== null);
}

function mergeIds(current, next) {
  return Array.from(new Set([...current.map(String), ...next.map(String)]));
}

function removePacketsForSeq(packets, event) {
  if (event.seq === null || event.seq === undefined) {
    return packets;
  }
  return packets.filter((packet) => String(packet.seq) !== String(event.seq));
}

function EventTimeline({ events }) {
  if (!events.length) {
    return <div className="table-state">Sem eventos recentes</div>;
  }

  return (
    <ol className="event-timeline">
      {events.slice().reverse().map((event, index) => (
        <li className={`event-${eventTone(event.type)}`} key={`${event.timestamp}-${event.type}-${event.seq ?? index}`}>
          <time>{formatTime(event.timestamp)}</time>
          <strong>{event.type}</strong>
          <span>{event.message ?? `Evento ${event.type}`}</span>
        </li>
      ))}
    </ol>
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

function getLatestNetworkState(events) {
  const visibleEvents = events.filter((event) => event.type !== "LOG_CREATED");
  const latest = visibleEvents[visibleEvents.length - 1];
  if (!latest) {
    return { activeLink: null, activeRouterId: null, tone: "neutral" };
  }

  return {
    activeLink: latest.next_hop
      ? { source: latest.router_id, target: latest.next_hop }
      : null,
    activeRouterId: latest.router_id ?? latest.destination ?? null,
    tone: eventTone(latest.type),
  };
}

function eventTone(type) {
  if (["PACKET_DROPPED", "PACKET_CORRUPTED", "MESSAGE_FAILED", "TIMEOUT"].includes(type)) {
    return "danger";
  }
  if (["ACK_SENT", "ACK_RECEIVED", "ACK_FORWARDED", "MESSAGE_DELIVERED"].includes(type)) {
    return "success";
  }
  if (["NAK_SENT", "NAK_RECEIVED", "NAK_FORWARDED", "MESSAGE_RETRY"].includes(type)) {
    return "warning";
  }
  if (
    [
      "MESSAGE_SENT",
      "MESSAGE_FORWARDED",
      "MESSAGE_RECEIVED",
      "MESSAGE_CREATED",
      "SIMULATION_SETTINGS_UPDATED",
      "LINK_COST_UPDATED",
      "LINK_CREATED",
      "LINK_REMOVED",
      "ROUTES_RECOMPUTED",
      "TOPOLOGY_LAYOUT_UPDATED",
      "TOPOLOGY_RANDOM_GENERATED",
      "TOPOLOGY_UPDATED",
    ].includes(type)
  ) {
    return "active";
  }
  return "neutral";
}

function isActiveGraphLink(activeLink, activeEdges, link) {
  return isSameLink(activeLink, link) || activeEdges.some((edge) => isSameLink(edge, link));
}

function isSameLink(activeLink, link) {
  if (!activeLink) {
    return false;
  }

  const activeSource = String(activeLink.source);
  const activeTarget = String(activeLink.target);
  const linkSource = String(link.source);
  const linkTarget = String(link.target);

  return (
    (activeSource === linkSource && activeTarget === linkTarget) ||
    (activeSource === linkTarget && activeTarget === linkSource)
  );
}

function formatTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function buildRouterPositions(routers) {
  return routers.reduce((positions, router) => {
    const routerId = String(router.id);
    const normalizedX = Number(router.x);
    const normalizedY = Number(router.y);
    positions[routerId] = {
      id: routerId,
      x: Number.isFinite(normalizedX) ? normalizedX * 100 : 50,
      y: Number.isFinite(normalizedY) ? normalizedY * 100 : 50,
    };
    return positions;
  }, {});
}

createRoot(document.getElementById("root")).render(<App />);
