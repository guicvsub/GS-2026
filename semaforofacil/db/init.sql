-- Contrato de dados do MVP. Todas as disciplinas leem/escrevem nestas tabelas.
CREATE TABLE IF NOT EXISTS semaforos (
  id          SERIAL PRIMARY KEY,
  cruzamento  TEXT NOT NULL,
  bairro      TEXT NOT NULL,
  latitude    DOUBLE PRECISION NOT NULL,
  longitude   DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS relatos (
  id                SERIAL PRIMARY KEY,
  semaforo_id       INTEGER REFERENCES semaforos(id),
  criado_em         TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- preenchidos pela Visão Computacional
  contraste         DOUBLE PRECISION,
  tamanho_relativo  DOUBLE PRECISION,
  classificacao     TEXT,            -- ok | baixo_contraste | pequena | nao_encontrada
  -- preenchidos pela IA Generativa
  descricao         TEXT,
  texto_relato      TEXT,
  -- controlado pelo fluxo (RPA atualiza no fim)
  status            TEXT NOT NULL DEFAULT 'rascunho',  -- rascunho | confirmado | registrado
  protocolo_156     TEXT
);

CREATE TABLE IF NOT EXISTS pontos_prioritarios (
  semaforo_id     INTEGER PRIMARY KEY REFERENCES semaforos(id),
  total_relatos   INTEGER NOT NULL,
  ultimo_relato   TIMESTAMPTZ,
  atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- DADOS SIMULADOS (documentar a geração no dicionário de dados).
-- Troque depois por dado aberto de semáforos de São Paulo.
INSERT INTO semaforos (cruzamento, bairro, latitude, longitude) VALUES
 ('Av. Paulista x R. Augusta', 'Consolação', -23.5558, -46.6603),
 ('Av. Paulista x Al. Santos', 'Cerqueira César', -23.5649, -46.6521),
 ('Av. Brigadeiro Faria Lima x R. Teodoro Sampaio', 'Pinheiros', -23.5671, -46.6959);
