# Relatório Prático — Implementação de Serviços com Docker

**Aluno(s):** Nathan Santana de Lima Babilonia
**Disciplina/Módulo:** Computação em Nuvem

## 1. Explicação linha a linha do Dockerfile

* `FROM python:3.12-slim`: Define a imagem base. Utilizamos a versão oficial do Python 3.12 na variante slim para manter o tamanho final do contêiner menor e mais seguro.
* `WORKDIR /app`: Cria (se não existir) e define o diretório `/app` dentro do contêiner como o local de trabalho padrão para os próximos comandos.
* `COPY requirements.txt .`: Copia o arquivo de dependências do host para o contêiner.
* `RUN pip install --no-cache-dir -r requirements.txt`: Instala as bibliotecas Python. O uso de `--no-cache-dir` evita que o pip armazene arquivos desnecessários em cache, reduzindo o tamanho da imagem. Fazemos isso antes de copiar o código para aproveitar o cache de camadas do Docker.
* `COPY . .`: Copia o restante do código da aplicação para dentro do `/app`.
* `ENV DATA_DIR=/app/data`: Define uma variável de ambiente informando à aplicação onde salvar os arquivos.
* `EXPOSE 8000`: Sinaliza que a aplicação dentro do contêiner estará ouvindo na porta 8000.
* `VOLUME /app/data`: Cria um ponto de montagem, indicando que os dados neste diretório devem persistir fora do ciclo de vida do contêiner.
* `CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]`: Define o comando padrão que será executado assim que o contêiner for iniciado, iniciando o servidor web Uvicorn (usado para FastAPI) para expor a aplicação na porta 8000 em todas as interfaces de rede (0.0.0.0).

## 2. Evidências da Execução (Etapas 3 a 6)

### Etapa 3 — Build da Imagem

*(Tamanho final e lista de camadas)*

```text
docker image ls notas-api
                                                                                                                                                             i Info →   U  In Use
IMAGE           ID            DISK USAGE   CONTENT SIZE   EXTRA
notas-api:1.0   2b41ad926ce0        223MB         54.5MB        

docker history notas-api:1.0
IMAGE          CREATED          CREATED BY                                      SIZE      COMMENT
2b41ad926ce0   22 seconds ago   CMD ["uvicorn" "app:app" "--host" "0.0.0.0" …   0B        buildkit.dockerfile.v0
<missing>      22 seconds ago   VOLUME [/app/data]                              0B        buildkit.dockerfile.v0
<missing>      22 seconds ago   EXPOSE [8000/tcp]                               0B        buildkit.dockerfile.v0
<missing>      22 seconds ago   ENV DATA_DIR=/app/data                          0B        buildkit.dockerfile.v0
<missing>      22 seconds ago   COPY app.py . # buildkit                        12.3kB    buildkit.dockerfile.v0
<missing>      22 seconds ago   RUN /bin/sh -c pip install --no-cache-dir -r…   26.3MB    buildkit.dockerfile.v0
<missing>      28 seconds ago   COPY requirements.txt . # buildkit              12.3kB    buildkit.dockerfile.v0
<missing>      28 seconds ago   WORKDIR /app                                    8.19kB    buildkit.dockerfile.v0
```

### Etapa 4 — Execução com Volume Nomeado

*(Criação do volume e inserção das primeiras notas)*

```text
docker volume create notas-dados
notas-dados

docker run -d --name notas -p 8000:8000 -v notas-dados:/app/data notas-api:1.0
3fce44b9b919cb51ce3475d7811a01c2e0b79b62d55e90768c8ea558b09734d2

curl.exe -X POST http://localhost:8000/notas -H "Content-Type: application/json" -d '{\"texto\": \"Teste de persistencia 1\"}'
{"texto":"Teste de persistencia 1","data_hora":"2026-09-18T14:51:44.975223"}
```

### Etapa 5 — Prova de Persistência

*(Destruição do contêiner original e acesso aos dados em um novo contêiner)*

```text
docker stop notas; docker rm notas
notas
notas

docker run -d --name notas2 -p 8000:8000 -v notas-dados:/app/data notas-api:1.0
65f5349417d6affb394d8bc71b607545cb61cadec9c5425d837d150cc7f7fe0d

curl.exe http://localhost:8000/notas
[{"texto":"Teste de persistencia 1","data_hora":"2026-09-18T14:51:44.975223"}]
```

### Etapa 6 — Contraexemplo (Efemeridade)

*(Demonstração da perda de dados sem o uso de volumes)*
**Explicação do motivo:** Quando não utilizamos a flag `-v`, os dados são gravados na camada temporária de leitura/escrita do próprio contêiner. Quando o contêiner é removido (`docker rm`), essa camada é apagada pelo Docker Engine e todos os dados criados ali são perdidos para sempre.

```text
docker run -d --name notas-efemero -p 8000:8000 notas-api:1.0
fdbe83e905c9c69b9cbb01cc7919c792288cf3299333d388c0ddf94eb5130538

curl.exe -X POST http://localhost:8000/notas -H "Content-Type: application/json" -d "{\`"texto\`": \`"Nota que vai sumir\`"}"
{"texto":"Nota que vai sumir","data_hora":"2026-09-18T14:54:30.317346"}

docker stop notas-efemero; docker rm notas-efemero  
notas-efemero
notas-efemero
```

## 3. Inspeção e Perguntas (Etapa 7)

**Onde, no host, o Docker armazena fisicamente o volume notas-dados?**
*Resposta:* O Docker armazena no diretório `/var/lib/docker/volumes/notas-dados/_data`, conforme atestado pela propriedade `Mountpoint` na inspeção do volume.

```text
docker volume inspect notas-dados
[
    {
        "CreatedAt": "2026-09-18T14:49:55Z",
        "Driver": "local",
        "Labels": null,
        "Mountpoint": "/var/lib/docker/volumes/notas-dados/_data",
        "Name": "notas-dados",
        "Options": null,
        "Scope": "local"
    }
]
```

**Qual é o conteúdo do diretório /app/data dentro do contêiner?**
*Resposta:* O diretório contém o arquivo `notas.json` criado pela aplicação Python.

```text
docker exec notas2 ls -la /app/data                                     
total 12
drwxr-xr-x 2 root root 4096 Sep 18 14:51 .
drwxr-xr-x 1 root root 4096 Sep 18 14:55 ..
-rw-r--r-- 1 root root   97 Sep 18 14:51 notas.json
```

**O que acontece com os dados se você executar `docker volume rm notas-dados` com o contêiner parado e removido?**
*Resposta:* O volume é excluído permanentemente do sistema de arquivos do host pelo Docker (apagando a pasta lá em `/var/lib/docker/volumes/...`). Consequentemente, o arquivo `notas.json` que estava lá dentro será apagado e os dados da aplicação serão perdidos de forma irreversível.

```text
docker stop notas2; docker rm notas2
notas2
notas2

docker volume rm notas-dados
notas-dados

docker volume inspect notas-dados
[]
Error response from daemon: get notas-dados: no such volume
```

## 4. Dificuldades e Aprendizados

Durante a execução da atividade, o principal ponto de atenção esteve na estruturação correta do `Dockerfile` para aproveitar o cache de camadas do Docker. Inicialmente, não é totalmente intuitivo o motivo de copiarmos o `requirements.txt` e instalarmos as dependências separadamente antes de copiar o restante do código-fonte. Contudo, na prática, essa abordagem otimizou consideravelmente o tempo de *build* nas tentativas subsequentes. Em relação aos aprendizados gerais, a atividade consolidou de forma muito clara o conceito de efemeridade dos contêineres. Observar, por meio dos testes, a perda irrecuperável de dados num ambiente sem mapeamento e contrastar isso com a estabilidade de um contêiner usando volumes (`-v`) demonstrou, na prática, a importância crucial do gerenciamento de estado e persistência para ambientes em produção.
