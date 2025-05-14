# Online Tracking System

## 1. Descrição do Projeto

O "Online Tracking System" é uma aplicação web distribuída desenvolvida como parte da unidade curricular de Sistemas Distribuídos e Segurança. O sistema permite o rastreio online de encomendas, oferecendo funcionalidades para o registo de utilizadores, registo de encomendas, consulta do estado das encomendas por parte dos utilizadores, e um painel de administração para gestão de encomendas e trajetos.

A comunicação entre a interface gráfica e os serviços de backend é realizada através de Web Services SOAP, e a aplicação é projetada para ser executada em containers Docker.

## 2. Arquitetura

O sistema é composto pelos seguintes componentes principais:

* **Interface Gráfica (GUI):** Uma aplicação web desenvolvida em Flask que permite a interação dos utilizadores e administradores com o sistema. Comunica com os Web Services via SOAP (utilizando Zeep como cliente).
* **Web Service 1 (WS1 - Utilizador):** Um serviço SOAP (desenvolvido com Flask e Spyne) responsável pelas operações dos utilizadores, como autenticação, registo, listagem e acompanhamento de encomendas.
* **Web Service 2 (WS2 - Administrador):** Um serviço SOAP (desenvolvido com Flask e Spyne) que disponibiliza operações administrativas, como gestão de encomendas (CRUD), gestão de utilizadores e atualizações de rastreio.
* **Base de Dados (DB):** Uma base de dados MySQL para persistência dos dados relativos a utilizadores, encomendas e informações de rastreio.

## 3. Tecnologias Utilizadas

* **Frontend (GUI):** Flask, Jinja2, Bootstrap
* **Backend (Web Services):** Python, Flask, Spyne (para exposição de serviços SOAP), Zeep (para consumo de serviços SOAP)
* **Base de Dados:** MySQL 8.0
* **Comunicação:** SOAP/XML
* **Segurança:** Hashing de passwords com Argon2
* **Containerização:** Docker, Docker Compose

## 4. Pré-requisitos

Para compilar e executar este projeto, necessitará do seguinte software instalado no seu sistema:

* **Docker:** [Instruções de Instalação do Docker](https://docs.docker.com/get-docker/)
* **Docker Compose:** [Instruções de Instalação do Docker Compose](https://docs.docker.com/compose/install/) (geralmente incluído com o Docker Desktop)

## 5. Configuração do Ambiente

1.  **Clonar o Repositório (se aplicável):**
    ```bash
    git clone <url_do_repositorio>
    cd <diretorio_do_projeto>
    ```

2.  **Variáveis de Ambiente para a Base de Dados:**
    Os serviços web (WS1 e WS2) requerem variáveis de ambiente para se conectarem à base de dados MySQL. Estas variáveis devem ser definidas num ficheiro `.env` na raiz do projeto, que será automaticamente lido pelo `docker-compose.yml`.

    Crie um ficheiro chamado `.env` com o seguinte conteúdo, substituindo os valores conforme necessário:

    ```env
    MYSQL_USER=user_db
    MYSQL_PASSWORD=password_db
    MYSQL_DATABASE=tracking_db
    MYSQL_HOST=db_mysql # Nome do serviço da base de dados no docker-compose.yml
    MYSQL_PORT=3306
    # Outras variáveis de ambiente que possam ser necessárias para os serviços
    ```
    **Nota:** O valor `MYSQL_HOST` deve corresponder ao nome do serviço da base de dados definido no seu ficheiro `docker-compose.yml` (por exemplo, `db` ou `db_mysql`).

3.  **Estrutura da Base de Dados:**
    A base de dados MySQL precisa de ter as tabelas necessárias criadas antes da primeira execução. O relatório menciona as seguintes tabelas principais:
    * `Utilizadores` (para autenticação/autorização)
    * `Pacotes` (para os itens de rastreio)
    * `InformacoesRastreio` (para as atualizações de estado)

    Poderá ser necessário um script SQL para inicializar o esquema da base de dados. Se existir um script (e.g., `init.sql`), este pode ser montado no container MySQL para execução automática no arranque. Consulte a configuração do serviço da base de dados no `docker-compose.yml` para verificar se esta automatização está implementada. Caso contrário, terá de criar as tabelas manualmente após o serviço da base de dados estar em execução.

## 6. Compilação (Build)

Com o Docker e Docker Compose instalados e as variáveis de ambiente configuradas, pode construir as imagens Docker para todos os serviços definidos no ficheiro `docker-compose.yml`:

```bash
docker-compose build

Este comando irá descarregar as imagens base necessárias e construir as imagens para a GUI, WS1, WS2 e a base de dados (se definida para ser construída a partir de um Dockerfile).

7. Execução
Após a compilação bem-sucedida das imagens, pode iniciar todos os serviços utilizando:

docker-compose up

Para executar os serviços em segundo plano (detached mode), utilize:

docker-compose up -d

Os serviços estarão acessíveis nos seguintes endereços (assumindo as portas padrão configuradas no docker-compose.yml):

Interface Gráfica (GUI): http://localhost:<PORTA_GUI> (e.g., http://localhost:5000)


Consulte o seu ficheiro docker-compose.yml para verificar as portas exatas que foram mapeadas para cada serviço.

Credenciais de Administrador Padrão:
O relatório menciona o login com uma conta pré-definida "Admin". Verifique se existem credenciais padrão ou se necessita de criar um utilizador administrador através de um script de inicialização da base de dados ou manualmente.

8. Parar a Aplicação
Para parar todos os serviços em execução, utilize (no mesmo diretório onde executou docker-compose up):

docker-compose down

Se desejar remover também os volumes (o que apagará os dados da base de dados, a menos que sejam volumes externos), pode usar:

docker-compose down -v

9. Estrutura do Projeto (Exemplo)
.
├── gui/                    # Código da Interface Gráfica
│   ├── app.py
│   ├── templates/
│   └── static/
│   └── Dockerfile
├── ws_user/                # Código do Web Service do Utilizador (WS1)
│   ├── ws1_user_service.py
│   ├── db_utils.py
│   └── Dockerfile
├── ws_admin/               # Código do Web Service do Administrador (WS2)
│   ├── ws2_admin_service.py
│   ├── db_utils.py
│   └── Dockerfile
├── db/                     # Configuração da Base de Dados (e.g., init.sql)
│   └── init.sql            # (Opcional, para criação de tabelas)
├── docker-compose.yml      # Ficheiro de orquestração do Docker Compose
├── .env                    # Ficheiro para variáveis de ambiente (NÃO COMMITAR SE CONTIVER SEGREDOS)
└── README.md               # Este ficheiro

10. Troubleshooting
Erro de Conexão à Base de Dados:

Verifique se as variáveis de ambiente no ficheiro .env (MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, MYSQL_HOST, MYSQL_PORT) estão corretas.

Certifique-se de que o nome do serviço MYSQL_HOST no .env corresponde ao nome do serviço da base de dados no docker-compose.yml.

Verifique os logs do container da base de dados: docker-compose logs <nome_do_servico_db>

Portas em Uso: Se receber erros a indicar que uma porta já está em uso, pode alterar o mapeamento de portas no docker-compose.yml (e.g., mudar "5000:5000" para "5050:5000") e aceder à aplicação na nova porta (http://localhost:5050).

Falhas na Construção de Imagens: Verifique os Dockerfiles de cada serviço para garantir que todas as dependências e comandos estão corretos. Analise a saída do comando docker-compose build para identificar o erro específico.

