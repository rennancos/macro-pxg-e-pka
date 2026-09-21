# PokeAlliance Hotkeys

## Perfis PKA e PXG

Selecione **PKA** ou **PXG** na lateral. O menu superior mostra os perfis do
jogo selecionado. Perfis antigos continuam sendo PKA, com suas macros preservadas.
O perfil PXG inicial fica vazio para voce configurar suas proprias acoes.

### Rotação PXG pela roda para baixo

No perfil PXG configurado, a macro de rotação aparece na aba Combo com o
gatilho **Roda p/ baixo**. Sua etapa define a tecla do revive (`Q`) e
o intervalo depois da troca (300 ms). A troca para o próximo slot é automática.
Depois de ativar as hotkeys, pressione `Ctrl+1` a `Ctrl+6` uma vez ou use o
botão **Sincronizar** na macro para indicar qual Pokémon está ativo. Cada giro
para baixo envia `Ctrl+N` para chamar o próximo Pokémon, espera 300 ms e envia
`Q` para reviver o que saiu; depois do slot 6, volta ao 1. `Ctrl+1` a `Ctrl+6` também
atualiza o slot acompanhado quando você troca manualmente. Ao desativar as
hotkeys ou trocar de perfil, é preciso sincronizar novamente. A rotação não
executa enquanto outra macro está em andamento.
Novos perfis pertencem ao jogo ativo; duplicar mantem o jogo e copia as macros.

Chat, intervalos, trava da roda, cancelamento e demais ajustes de execucao sao
salvos separadamente por jogo. Aparencia e tamanho da janela continuam globais.
Na aba Configuracoes do PXG, use **Selecionar executavel** para escolher o cliente
do jogo (nao o launcher), e salve. Depois configure Skills, Hotkeys e Combo.
A troca de perfil cancela a macro em andamento antes de carregar o destino.
A compatibilidade do envio de teclas com o PXG precisa ser testada no cliente.

Gerenciador de hotkeys para Windows feito para acelerar o uso manual de skills,
Revive e comandos de chat no PokeAlliance.

**O que este programa faz:** ouve as teclas que *você* configura e, quando você
aperta uma delas, envia a tecla ou o comando correspondente ao jogo.

**O que este programa não faz:** não joga sozinho, não identifica inimigos, não
lê a memória do jogo, não faz leitura de tela, não faz farm automático e não
executa nenhum ciclo repetido. Toda ação começa em uma tecla pressionada por
você. Nada é enviado para a internet — o funcionamento é 100% local.

---

## 1. Requisitos

| Item | Versão |
|------|--------|
| Windows | 10 ou 11 |
| Python | 3.12 ou superior ([python.org](https://www.python.org/downloads/windows/) — marque **Add python.exe to PATH** no instalador) |

Dependências (instaladas via `requirements.txt`):

- `customtkinter` — interface gráfica dark mode
- `keyboard` — hotkeys globais e envio de teclas no Windows
- `mouse` — gatilhos pela roda do mouse (a `keyboard` não enxerga o mouse)
- `pyinstaller` — geração do `.exe`

> ### ⚠️ Administrador é obrigatório
>
> O PokeAlliance abre como administrador (confirmado por medição). Sem elevação,
> o programa falha de **duas** formas, ambas silenciosas:
>
> 1. **Não consegue enviar teclas.** O Windows descarta entrada sintética
>    dirigida a uma janela de integridade mais alta. Sem erro, sem exceção.
> 2. **Não recebe os gatilhos.** Um hook global de teclado/mouse em processo
>    não elevado para de receber eventos enquanto uma janela elevada está em
>    foco — a roda do mouse simplesmente nunca dispara dentro do jogo.
>
> O log mostra o sintoma assim: as macros só aparecem quando você rola a roda
> **fora** do jogo, e aí são recusadas com *"o jogo não está em primeiro
> plano"*. Dentro do jogo, nada é registrado.
>
> **O `.exe` já pede elevação sozinho** (manifesto `requireAdministrator`):
> basta aceitar o UAC ao abrir.
>
> **Em desenvolvimento** (`python main.py`), o manifesto não vale. O programa
> detecta que não está elevado e oferece reabrir como administrador. Para evitar
> o aviso, abra o PowerShell como administrador antes de rodar.

## 2. Ambiente virtual

Abra o PowerShell na pasta do projeto:

```powershell
cd pokealliance_hotkeys
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativação:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## 3. Instalação das dependências

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Execução em desenvolvimento

```powershell
python main.py
```

Checagens (nenhuma envia teclas ao sistema nem grava no seu perfil):

```powershell
python selfcheck.py    # lógica: perfis, macros, trava da roda, detecção de janela
python smoketest.py    # interface: monta as 7 páginas e exercita a edição
```

Na primeira execução são criados `config/settings.json`, um perfil padrão em
`config/profiles/` e a pasta `logs/`.

## 5. Configuração das hotkeys

> **Como o PokeAlliance já usa o teclado.** O cliente ocupa `F1`–`F12` (as 12
> moves do Pokémon), `WASD`, setas, Numpad, `Q Z C E T R X F P`, `Space`, `Tab`,
> `] \` e quase todo `Ctrl+letra`. Escolher uma dessas teclas como hotkey do app
> causa conflito. Livres: `B G H I J K L M N O U V Y`, `Numpad0`, `Numpad5`,
> `Insert`, `Delete`, `Home`, `End`, `PageUp/Down`, `Pause`, `ScrollLock`,
> `[ ; ' , . / - =`. O Dashboard lista os conflitos detectados.

**As skills já funcionam sozinhas no jogo.** Por isso o perfil padrão deixa a
*hotkey* de cada skill **vazia**: mapear `F1` no app só para reenviar `F1` ao
jogo é uma ponte inútil que ainda rouba a tecla do cliente. Preencha a hotkey
apenas se quiser disparar a skill por **outra** tecla.

Na aba **Skills**, selecione uma skill na lista e use o editor ao lado.
Trocar de skill ou de tela preserva o rascunho; **Salvar skills** grava as
alteracoes e **Descartar alteracoes** restaura os valores salvos.
O editor tem os seguintes campos:

| Campo | Significado |
|-------|-------------|
| **Hotkey** | a tecla que *você* aperta no teclado |
| **Tecla no jogo** | a tecla que o programa envia ao PokeAlliance |
| **Toque (ms)** | tempo entre pressionar e soltar a tecla enviada |
| **Ativa** | desmarque para ignorar a skill sem apagar a configuração |

Clique em **Gravar** e pressione a tecla desejada — o campo é preenchido
sozinho. Enquanto a gravação está em andamento as ações ficam pausadas, então a
tecla capturada não dispara nada no jogo.

Botões no topo da janela:

- **ATIVAR HOTKEYS / DESATIVAR HOTKEYS** — liga e desliga tudo.
- **`Pause`** (configurável) — parada de emergência. Funciona mesmo com o jogo em
  primeiro plano: desativa tudo e cancela qualquer macro na hora.
  ⚠️ **Não use `F12`**: no PokeAlliance, F12 é a *move 12* do Pokémon.

### Só executar com o jogo em foco

Ligada por padrão (aba Configurações). Antes de qualquer envio, o app confere se
a janela em primeiro plano é `PokeAlliance_dx.exe` ou `PokeAlliance_gl.exe`.

**Não desligue se você usa gatilhos na roda do mouse** — sem isso, rolar a roda
no navegador digitaria `!offensive` dentro dele.

A verificação usa `PROCESS_QUERY_LIMITED_INFORMATION`, o direito mínimo do
Windows, que tecnicamente **não permite** ler memória do jogo.

A opção *"Bloquear a tecla da hotkey para o jogo"* (aba Configurações) evita que
a tecla que você apertou chegue ao jogo junto com a tecla enviada pelo programa.
Deixe ligada, exceto se quiser que a tecla original também funcione no jogo.
A hotkey de cancelar combo e a de emergência **nunca** são bloqueadas.

## 6. Criação de perfis

Aba **Pokemon**:

- **Novo** — cria um perfil com o layout padrão.
- **Duplicar** — copia o perfil ativo com outro nome.
- **Renomear** — altere o nome no campo à direita e clique em Renomear.
- **Excluir** — remove o perfil (sempre resta pelo menos um).
- Clicar no nome na lista da esquerda ativa o perfil.

Cada perfil vira um arquivo JSON:

```
config/
├── settings.json
└── profiles/
    ├── charizard.json
    └── blastoise.json
```

Trocar de perfil recarrega skills, ações e combo, e reaplica as hotkeys na hora.

## 7. Offensive / Defensive / Revive

Aba **Hotkeys**. Cada ação tem dois modos:

**Modo Tecla** — aperta uma tecla no jogo (usual para o Revive).

**Modo Comando no chat** — a sequência executada é:

1. envia a tecla de abrir o chat (Configurações → *Abrir chat*, padrão `Enter`);
2. digita o comando, ex. `!offensive`;
3. envia a tecla de confirmação (padrão `Enter`).

Isso só acontece quando você aperta a hotkey configurada. O indicador
**OFFENSIVE / DEFENSIVE** no topo da janela é apenas visual: mostra a última
ação enviada, não o estado real dentro do jogo.

Se o comando sair truncado, aumente *Digitação (ms/tecla)* e as pausas na aba
Configurações — alguns clientes perdem caracteres quando a digitação é rápida.

## 8. Macros (aba Combo)

Uma macro é uma sequência de etapas disparada por **um** gatilho. Cada etapa é de
um destes três tipos:

| Tipo | O que faz |
|---|---|
| **Skill** | envia a tecla do slot de skill do perfil |
| **Tecla** | envia uma tecla avulsa (ex.: `Q`, o item de revive na barra de ação) |
| **Comando** | abre o chat, digita o texto e envia com Enter |

Para montar: escolha a macro na lista à esquerda, defina nome e gatilho,
adicione etapas com **+ Etapa**, reordene com `^` e `v`, e clique em **Salvar**.

### Gatilho pela roda do mouse

No campo **Gatilho**, além de `Teclado` existem `Roda p/ cima` e `Roda p/ baixo`.

O perfil padrão já vem com as duas macros montadas, **usando apenas teclas que o
jogo já reconhece**:

```
Ofensiva  (roda para cima)
  tecla  r        ->  !offensive   (ACTION_BAR_8)    esperar 200 ms
  tecla  t        ->  !autocombo   (ACTION_BAR_5)    esperar   0 ms

Defensiva (roda para baixo)
  tecla  q        ->  item de revive (ACTION_BAR_1)  esperar 200 ms
  tecla  e        ->  !defensive   (ACTION_BAR_4)    esperar   0 ms
```

### Por que tecla e não comando no chat

O PokeAlliance já tem esses comandos gravados na barra de ação, cada um numa
tecla. Mandar a tecla é melhor que digitar no chat em todos os aspectos:

| | Tecla | Comando no chat |
|---|---|---|
| eventos enviados | 1 | ~6 (abrir, digitar, enviar, fechar) |
| depende do chat estar travado/destravado | não | sim |
| deixa rastro no histórico de conversa | não | sim |
| risco de sair truncado | não | sim |

E há uma armadilha concreta no modo comando: depois do Enter, o cliente pode
deixar o **campo de chat com o foco**. A etapa seguinte então digita dentro
dele — a tecla `q` do revive vira a *letra* `q`, e o Enter seguinte publica isso
como mensagem no chat. Se você usar o modo comando, configure a tecla
**Fechar chat** (Configurações), que é enviada ao final de cada comando para
evitar exatamente isso.

Se as suas teclas forem outras, troque na aba **Combo**: o botão **Gravar**
captura a tecla que você apertar.

**Duas ressalvas sobre a roda:**

1. Um giro físico da roda gera 3–5 eventos. A **trava da roda** (400 ms por
   padrão, em Configurações) faz só o primeiro disparar. Se a macro repetir,
   aumente esse valor.
2. A rolagem **também chega ao jogo** — diferente das teclas, a roda não pode ser
   bloqueada. Se a roda fizer algo no PokeAlliance, isso vai acontecer junto.

### Execução

A macro roda em uma thread separada — a interface continua respondendo. Executa
**uma vez** por acionamento; não existe repetição automática. `Esc` (configurável),
o botão **Cancelar execução** ou a parada de emergência interrompem na hora,
inclusive no meio de uma espera. Uma nova macro só começa depois que a anterior
termina.

O intervalo entre etapas nunca deve ficar abaixo de **30 ms**: é o `hotkeyDelay`
do próprio cliente, e abaixo disso ele engole eventos.

## 9. Gerar o `.exe`

Com o ambiente virtual criado e as dependências instaladas:

```powershell
.\build.bat
```

Resultado:

```
dist\PKA_PXG_Hotkeys\PKA_PXG_Hotkeys.exe
```

Mantenha a pasta `_internal` junto do executavel. A distribuicao em pasta evita
extrair as dependencias a cada abertura. Os perfis ficam em `config/` ao lado
do executavel; faca uma copia dessa pasta antes de reconstruir a distribuicao.

O build usa `--onedir --windowed --noupx` e `--collect-all customtkinter` (os temas do
CustomTkinter são arquivos de dados e precisam ser embutidos explicitamente).

O executável é portátil: `config/` e `logs/` são criados **ao lado do .exe** na
primeira execução, não dentro do pacote temporário. Para levar suas
configurações para outra máquina, copie a pasta `config/` junto.

## 10. Troubleshooting

| Sintoma | Causa provável / solução |
|---------|--------------------------|
| Roda não dispara nada dentro do jogo, e o log fica vazio | Falta elevação: o hook não recebe eventos enquanto a janela elevada do jogo está em foco. Abra como administrador (o `.exe` pede o UAC sozinho). |
| Log diz "o jogo não está em primeiro plano" | Está correto: no momento da rolagem, a janela em foco era outra (navegador, Explorer, o próprio app). Clique dentro do jogo antes de acionar. |
| A tecla chega ao jogo mas nada acontece | O nome da tecla enviada está errado. Use o botão **Gravar** no campo *Tecla no jogo* em vez de digitar. |
| Hotkey ignorada ao ativar | Aparece um aviso listando duplicadas/inválidas. O Dashboard também mostra os conflitos. Duas ações não podem usar a mesma tecla. |
| Numpad `+` / `-` não funciona | Grave a tecla pelo botão **Gravar**. A biblioteca identifica o numpad pelo código físico; digitar `num +` manualmente nem sempre funciona. |
| Comando sai incompleto no chat | Aumente *Digitação (ms/tecla)* e *Pausa após abrir* em Configurações. |
| A tecla original parou de funcionar no jogo | A opção *Bloquear a tecla da hotkey para o jogo* está ligada. Desligue-a ou escolha outra hotkey. |
| A macro da roda dispara várias vezes | Um giro gera 3–5 eventos. Aumente a **trava da roda** em Configurações (400 ms → 600 ms). |
| A roda não dispara nada | Verifique se a lib `mouse` está instalada e se o PokeAlliance está em primeiro plano (a opção *só executar com o jogo em foco* vem ligada). |
| A roda mexe em algo dentro do jogo | Esperado: a rolagem não pode ser bloqueada, ela chega ao jogo junto com a macro. Use uma tecla em vez da roda se atrapalhar. |
| `ImportError: No module named customtkinter` | O ambiente virtual não está ativo. Rode `.\.venv\Scripts\Activate.ps1`. |
| O antivírus bloqueia o `.exe` | Executáveis do PyInstaller que usam hooks de teclado geram falso positivo. Libere a pasta `dist\` no antivírus. |
| Erro ao registrar hotkeys / `keyboard` não carrega | Rode como administrador; em último caso reinstale com `pip install --force-reinstall keyboard`. |

Os registros ficam em `logs/app.log` e na aba **Logs**. São gravadas apenas as
ações do próprio programa (perfil carregado, hotkeys ativadas, skill executada).
Nada do que você digita fora dessas ações é registrado — não existe captura de
digitação no código.

---

## Estrutura do projeto

```
pokealliance_hotkeys/
├── main.py                      ponto de entrada
├── selfcheck.py                 checagem da lógica sem GUI
├── smoketest.py                 checagem da interface (pega erro de callback)
├── build.bat                    gera dist/PKA_PXG_Hotkeys/PKA_PXG_Hotkeys.exe
├── requirements.txt
├── app/
│   ├── constants.py             valores centralizados
│   ├── gui/                     interface (não conhece a lib de teclado)
│   │   ├── main_window.py       janela, sidebar, barra de status
│   │   ├── dashboard.py         perfil, status, modo, última ação
│   │   ├── skills_page.py       skills 1..6
│   │   ├── combo_page.py        editor da sequência
│   │   ├── profiles_page.py     CRUD de perfis
│   │   ├── hotkeys_page.py      Revive / Offensive / Defensive
│   │   ├── settings_page.py     chat, emergência, aparência
│   │   ├── logs_page.py
│   │   └── widgets.py           widgets reutilizáveis + BasePage
│   ├── services/
│   │   ├── controller.py        cola entre GUI, configuração e execução
│   │   ├── hotkey_manager.py    único ponto que registra hotkeys globais
│   │   ├── wheel_manager.py     gatilhos da roda do mouse + trava anti-repetição
│   │   ├── window_manager.py    checa se o jogo está em primeiro plano
│   │   ├── action_executor.py   único ponto que envia teclas
│   │   ├── combo_manager.py     macros em thread + cancelamento
│   │   ├── profile_manager.py   perfis em disco
│   │   └── settings_manager.py  settings.json
│   ├── models/
│   │   ├── profile.py           dataclasses do perfil (+ validação)
│   │   └── settings.py
│   └── utils/
│       ├── paths.py             caminhos (dev e PyInstaller)
│       ├── jsonio.py            JSON atômico e tolerante a corrupção
│       └── logger.py            log em arquivo + buffer da GUI
├── config/                      gerado na 1ª execução
└── logs/
```

O que é salvo automaticamente ao fechar: perfil ativo, skills, hotkeys, delays,
comandos, preferências e o tamanho/posição da janela.
