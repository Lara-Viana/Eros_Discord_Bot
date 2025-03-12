# Eros - Um Bot de Discord inspirado no Mudae

O **Eros** é um bot de Discord inspirado no famoso bot **Mudae**, que permite aos usuários "paquerar", tentar conquistar e "casar" com personagens adicionados ao banco de dados. Além disso, o bot inclui um sistema de economia baseado em "Eritos", que podem ser coletados e usados para trocar personagens entre usuários. O bot também permite a personalização de vantagens para personagens específicos, tendo uma vantagem maior durante as tentativas de conquista.

---

## Funcionalidades Principais

### 1. **Paquerar Personagens**
   - Comando: `/paquerar`
   - Descrição: O bot seleciona um personagem aleatório disponível para o usuário tentar conquistar. O sucesso é determinado por um sistema de rolagem de dados, onde o usuário precisa tirar um número maior ou igual ao número do personagem (com sua vantagem aplicada).
   - Cooldown: O usuário pode tentar conquistar personagens até 5 vezes a cada 18 horas. Após 5 tentativas, o usuário deve esperar o cooldown para tentar novamente.

### 2. **Casar com Personagens**
   - Comando: `/paquerar` (após conquistar o personagem)
   - Descrição: Se o usuário conseguir conquistar um personagem, ele automaticamente "casa" com ele. O personagem é adicionado à lista de "amores" do usuário.
   - Cooldown: O usuário só pode se casar uma vez a cada 18 horas.

### 3. **Divorciar de Personagens**
   - Comando: `/divorciar <nome_do_personagem>`
   - Descrição: Permite ao usuário se divorciar de um personagem que ele conquistou, liberando-o para que outros usuários possam conquistá-lo.

### 4. **Listar Personagens Conquistados**
   - Comando: `/meus_amores`
   - Descrição: Exibe uma lista de todos os personagens que o usuário conquistou, dividida em páginas de 15 personagens cada.

### 5. **Adicionar Personagens**
   - Comando: `/adicionar_personagem <nome> <imagem_url>`
   - Descrição: Permite que qualquer usuário adicione um novo personagem ao banco de dados. O personagem será disponibilizado para todos os usuários do bot.
   - Exemplo: `/adicionar_personagem "Goku" "https://exemplo.com/goku.jpg"`

### 6. **Sistema de Economia (Eritos)**
   - **Coletar Eritos**
     - Comando: `/coletar`
     - Descrição: Permite ao usuário coletar uma quantidade aleatória de Eritos a cada 18 horas.
   - **Ver Saldo**
     - Comando: `/saldo`
     - Descrição: Exibe a quantidade de Eritos que o usuário possui.
   - **Ver Saldo de Outro Usuário**
     - Comando: `/ver_saldo <usuário>`
     - Descrição: Exibe a quantidade de Eritos de outro usuário.
   - **Oferecer Troca**
     - Comando: `/oferecer_troca <personagem> <destinatario> <quantidade_eritos>`
     - Descrição: Permite ao usuário oferecer um personagem que ele conquistou em troca de Eritos de outro usuário.
   - **Aceitar/Recusar Troca**
     - Descrição: O destinatário da troca pode aceitar ou recusar a proposta de troca.

### 7. **Ranking de Eritos**
   - Comando: `/rank`
   - Descrição: Exibe o top 10 usuários com mais Eritos.

### 8. **Vantagens Personalizadas para Personagens**
   - **Definir Vantagem**
     - Comando: `/definir_vantagem <nome_do_personagem> <vantagem>`
     - Descrição: Permite ao dono do bot definir uma vantagem personalizada para um personagem específico. Por exemplo, **Goku** pode ter uma vantagem de +15.
     - Exemplo: `/definir_vantagem "Goku" 15`

### 9. **Comandos de Administração**
   - **Excluir Personagem**
     - Comando: `/excluir_personagem <nome>`
     - Descrição: Remove um personagem do banco de dados. Apenas o dono do bot pode usar este comando.
   - **Limpar Todos os Amores**
     - Comando: `/resetar_status`
     - Descrição: Remove todos os relacionamentos e marca todos os personagens como disponíveis. Apenas o dono do bot pode usar este comando.
   - **Resetar Cooldowns**
     - Comando: `/resetar_cooldowns`
     - Descrição: Reseta o cooldown de paquera, casamento e coleta de Eritos de todos os usuários. Apenas o dono do bot pode usar este comando.
   - **Alterar Imagem de Personagem**
     - Comando: `/alterar_imagem_personagem <nome> <nova_imagem_url>`
     - Descrição: Permite ao dono do bot alterar a imagem de um personagem.

---

## Configuração

### 1. **Clone o Repositório**

### 2. **Instalação das Dependências**
   - O bot utiliza as seguintes bibliotecas Python:
     - `discord.py`: Para interagir com a API do Discord.
     - `aiosqlite`: Para gerenciar o banco de dados SQLite de forma assíncrona.
     - `datetime`: Para manipulação de datas e horários.
     - `random`: Para gerar números aleatórios.

   - Instale as dependências necessárias usando o `pip`:
     ```
     pip install discord.py 
     ```
     
### 3. **Configuração do Bot**
   - No arquivo `bot.py`, substitua `'Seu Token'` pelo token do seu bot do Discord.
   - Defina o ID do dono do bot na variável `SEU_ID`.

### 4. **Execute o Bot**

---

## Estrutura do Banco de Dados

O bot utiliza um banco de dados SQLite (`eros.db`) para armazenar informações sobre personagens, usuários, amores, cooldowns e Eritos. Abaixo está a estrutura das tabelas:

- **personagens**: Armazena os personagens disponíveis para conquista.
  - `id`: ID único do personagem.
  - `nome`: Nome do personagem.
  - `imagem`: URL da imagem do personagem.
  - `conquistado`: Indica se o personagem foi conquistado (0 = disponível, 1 = conquistado).
  - `vantagem`: Vantagem do personagem durante as tentativas de conquista (padrão: +2).

- **amores**: Armazena os relacionamentos entre usuários e personagens.
  - `usuario_id`: ID do usuário que conquistou o personagem.
  - `personagem`: Nome do personagem conquistado.

- **cooldowns**: Armazena informações sobre cooldowns de comandos.
  - `usuario_id`: ID do usuário.
  - `tentativas`: Número de tentativas de paquera.
  - `tempo`: Tempo de cooldown para tentativas de paquera.
  - `ultimo_casamento`: Último momento em que o usuário se casou.
  - `ultimo_coletar`: Último momento em que o usuário coletou Eritos.

- **moedas**: Armazena a quantidade de Eritos dos usuários.
  - `usuario_id`: ID do usuário.
  - `eritos`: Quantidade de Eritos do usuário.

- **trocas**: Armazena propostas de troca entre usuários.
  - `id`: ID único da troca.
  - `ofertante_id`: ID do usuário que ofereceu a troca.
  - `personagem`: Nome do personagem oferecido.
  - `destinatario_id`: ID do usuário que recebeu a proposta.
  - `quantidade_eritos`: Quantidade de Eritos oferecidos.

---
Contribuições são bem-vindas!
