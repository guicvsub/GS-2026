# Assistente de Mobilidade por Ônibus

Aplicativo de apoio à mobilidade de pessoas cegas ou com baixa visão. A proposta é ajudar a identificar o ônibus que chegou ao ponto e acompanhar a viagem por meio de alertas acessíveis.

## Como funciona

O usuário escolhe a linha ou rota no aplicativo. Uma câmera ESP32-CAM captura o letreiro do ônibus e envia a imagem para o celular. O sistema tenta reconhecer a linha e, quando corresponde à rota escolhida, avisa o usuário por áudio e vibração. O GPS do celular poderá ser usado para avisar quando estiver perto do ponto de descida.

## Tecnologias previstas

- **Interface:** HTML, CSS e JavaScript
- **Lógica, processamento de imagens e integrações:** Python e APIs
- **Banco de dados:** MySQL
- **Exploração e preparação de dados:** Python e Google Colab
- **Dispositivo:** ESP32-CAM
- **Automação:** UiPath, se fizer sentido para o processo escolhido
- **Case do dispositivo:** impressão 3D

As tecnologias e funcionalidades ainda podem ser ajustadas durante o desenvolvimento.

## Equipe

| Integrante | RM |
|---|---|
| Guilherme Santiago da Silva | RM552321 |
| Gabriel Souza Fiore | RM553710 |
| Gustavo Govea Soares | RM553842 |
| Pedro Henrique Mello Silva Alves | RM554223 |
| Gabriel Borba | RM553187 |

## 📊 Componente Dados — Big Data Architecture & Data Integration

Pipeline orquestrado no Apache Airflow que leva o GTFS da SPTrans do dado bruto até tabelas curadas no MySQL, com dicionário de dados, diagrama de arquitetura e prints de execução.

- [README do componente Dados](GS/GS/citizentech-dados/README.md)
- [PDF único de entrega (arquitetura + dicionário + evidências)](GS/GS/citizentech-dados/docs/Entrega_BigData_CitizenTech.pdf)
- [Prints do Airflow](GS/GS/citizentech-dados/docs/evidencias/prints_airflow/)

## Status

Projeto em desenvolvimento. A cidade piloto, as fontes de dados e os detalhes de implementação serão definidos pela equipe.
