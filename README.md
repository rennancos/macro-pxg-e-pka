# PKA / PXG Hotkeys

Aplicativo local para Windows com perfis separados de PokeAlliance (PKA) e PXG. Executa skills, atalhos, comandos de chat e sequências finitas disparadas pelo usuário, usando teclado, roda ou botões laterais do mouse.

**Estado da distribuição:** a revisão de 26/09/2026 encontrou uma pendência de segurança na perda de foco durante a execução. Consulte [SECURITY.md](SECURITY.md) antes de distribuir. A aprovação dos testes não equivale à validação dentro do jogo.

## Começar pelo executável

1. Extraia a pasta inteira `PKA_PXG_Hotkeys`, mantendo `_internal` junto do `.exe`. Use uma pasta na qual você possa gravar configurações.
2. Abra `PKA_PXG_Hotkeys.exe`. O build atual solicita administrador pelo UAC, necessário para interagir com clientes que também estejam elevados.
3. Selecione **PKA** ou **PXG** na lateral. Em **Configurações**, selecione o executável do cliente do jogo, não o launcher.
4. Configure suas teclas e macros. Os perfis pessoais do autor não acompanham uma distribuição limpa; o perfil PXG inicial é vazio.
5. Mantenha **Só executar com o jogo em foco** habilitado e confira a tecla de emergência, por padrão `Pause`.
6. Ative as hotkeys e teste uma ação por vez com o jogo em primeiro plano.

As configurações e os logs são criados em `config/` e `logs/`, ao lado do executável. Faça backup de `config/` antes de atualizar. Não substitua seus perfis por arquivos de outra pessoa sem revisar os atalhos e comandos.

## Configuração

- **Skills:** tecla de gatilho, tecla enviada ao jogo e duração do toque. Uma skill pode continuar sendo usada diretamente pelo jogo, sem remapeamento.
- **Hotkeys:** ações individuais como Revive, Offensive e Defensive, por tecla ou comando de chat.
- **Combo:** macros com etapas de skill, tecla ou comando. O intervalo de uma etapa é a espera antes da próxima; o intervalo da última não acrescenta uma espera final.
- **Pokémon:** criação, duplicação e seleção de perfis do jogo ativo.
- **Logs:** sequência das ações enviadas, esperas, coordenadas, duração, recusas e erros.

As teclas do jogo precisam estar configuradas no próprio cliente. `Q` para revive e `Ctrl+1` a `Ctrl+6` para troca são exemplos usados no desenvolvimento, não uma garantia de configuração em qualquer instalação.

A roda e os botões do mouse também podem chegar ao jogo. A trava da roda reduz múltiplos disparos de um giro; não bloqueia a ação nativa do cliente. Só uma macro roda por vez.

## Troca de Pokémon no PXG

Uma macro marcada como troca (`switch: true` no JSON) envia um único `Ctrl+N` por acionamento, seguindo os atalhos válidos das suas etapas. Exemplo: `Ctrl+1, Ctrl+2, Ctrl+4` percorre `1 → 2 → 4 → 1`.

No painel da macro, escolha **Pokémon atual** e clique em **Sincronizar**. Trocas manuais por `Ctrl+1` a `Ctrl+6` também atualizam o slot acompanhado quando as hotkeys estão ativas e o contexto permite. A troca e o revive compartilham esse registro. Clicar no retrato não atualiza o slot: sincronize novamente.

Sem sincronização, a troca começa pelo primeiro slot da lista efetiva. Há duas limitações conhecidas:

- Com menos de dois atalhos válidos, a lista efetiva passa a ser `1, 2, 3, 4, 5, 6`. Uma lista contendo apenas `Ctrl+4` começa pelo **1** quando não há sincronização.
- Atalhos repetidos podem prender o ciclo. Use slots únicos; `1, 2, 1, 3` alterna entre 1 e 2.

Os marcadores `switch` e `rotation` são propriedades do perfil; dar o nome “trocar Pokémon” a uma macro comum não ativa esse modo. O perfil PXG vazio não inclui esses modos prontos. Perfis de exemplo destinados a terceiros precisam ser preparados e revisados separadamente.

## Revive e cursor no PXG

O código atual da rotação com revive (`rotation: true`) troca para o próximo slot, espera o intervalo configurado e envia a tecla de revive. Quando há pelo menos duas posições de retratos pequenos configuradas nos cinco primeiros `team_slots`, ele também:

1. Lê pixels próximos às barras de vida, em memória, para procurar um retrato com barra vazia.
2. Move o cursor até o alvo e clica, mantendo o ponteiro sobre ele durante o revive.
3. Restaura a posição anterior do cursor ao finalizar. Cancelamento e erro também solicitam a restauração.

Sem posições suficientes, o fluxo atual envia o revive sem clique e registra um aviso. Se a busca visual não encontra um alvo, a macro interrompe antes do revive. As posições e os limiares de cor dependem de resolução, escala e layout; essa identificação é experimental e pode escolher o alvo errado. Não distribua coordenadas pessoais como se fossem universais.

O movimento rápido até o retrato e de volta pode parecer que o mouse “sumiu”. A troca simples não precisa mover o cursor. Não há leitura da memória do processo do jogo, mas **há leitura de pixels da tela** no modo descrito acima.

## Cancelamento e segurança

`Esc` cancela a macro por padrão; `Pause` desativa as hotkeys e solicita o cancelamento. As teclas são configuráveis. As esperas entre etapas são interrompíveis, mas um envio de tecla ou comando que já começou pode terminar antes de o cancelamento ser observado.

**Limitação conhecida:** o foco é verificado ao iniciar; não há uma verificação geral antes de cada envio posterior. Trocar de janela durante a macro pode mandar entradas à outra janela. Não use a macro em paralelo com outras janelas enquanto essa pendência estiver aberta. Detalhes e reprodução em [SECURITY.md](SECURITY.md).

O código da aplicação revisado não implementa telemetria, login, atualização remota nem envio de dados pela rede. Usa hooks globais para atalhos e gravação de gatilhos, além de entrada sintética. Isso não é uma certificação das dependências ou dos binários distribuídos.

Os logs incluem nomes de perfis, teclas, texto dos comandos configurados e coordenadas. Revise-os antes de compartilhar. Não coloque senhas ou tokens nas macros. Os registros confirmam o envio pelo programa, não a aceitação pelo jogo.

Se o antivírus detectar o pacote, interrompa o uso e investigue o arquivo e sua origem. Não desative a proteção nem crie exclusões amplas. Este projeto não garante autorização de uso pelos jogos.

## Executar pelo código

Requisitos do ambiente validado: Windows, Git, Python 3.12 e Tcl/Tk funcional.

No PowerShell, clone o [repositório do projeto](https://github.com/rennancos/macro-pxg-e-pka), entre na pasta e instale as dependências:

```powershell
git clone https://github.com/rennancos/macro-pxg-e-pka.git
cd macro-pxg-e-pka
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Não é necessário ativar o ambiente virtual para usar esses comandos. A aplicação oferece reabertura com elevação quando necessária.

## Testes

Os testes usam entradas simuladas e configurações temporárias; não validam a aceitação das ações pelo jogo.

```powershell
.\.venv\Scripts\python.exe selfcheck.py
.\.venv\Scripts\python.exe -m unittest test_security test_rotation test_navigation test_game_profiles
.\.venv\Scripts\python.exe smoketest.py
```

Os testes de interface precisam de uma sessão gráfica e Tcl/Tk disponível. `Can't find a usable init.tcl` indica problema de instalação ou localização do Tcl/Tk. No ambiente da revisão, os testes passaram usando as pastas `_tcl_data` e `_tk_data` de um build local conhecido, via `TCL_LIBRARY` e `TK_LIBRARY`.

`test_security` mantém uma falha esperada documentada para a perda de foco entre etapas. `OK (expected failures=1)` **não** significa ausência de riscos. Veja resultados e limites em [SECURITY.md](SECURITY.md).

## Gerar e compartilhar

```powershell
.\build.bat
```

Resultado: `dist/PKA_PXG_Hotkeys/PKA_PXG_Hotkeys.exe`, acompanhado de `_internal/`. Faça backup de configurações antes de reconstruir: o empacotador pode substituir a pasta de saída.

Para entregar a terceiros, use uma cópia limpa contendo o executável, `_internal/`, README e o relatório de segurança. Não inclua `config/`, `logs/`, backups, capturas de tela, `.venv/`, ferramentas de auditoria ou arquivos de builds anteriores. Se fornecer um perfil de exemplo, revise os comandos, caminhos e coordenadas antes.

O `.gitignore` protege arquivos locais de novos commits; não remove arquivos que já tenham sido versionados. Ele também não filtra o conteúdo de um ZIP montado manualmente. Confira o conteúdo do pacote final e teste a primeira execução sem configurações pessoais.

As dependências de `requirements.txt` usam versões mínimas, portanto builds futuros podem instalar versões diferentes. Repita a auditoria no ambiente usado para gerar cada versão. Não há arquivo de licença do projeto nesta revisão; defina os termos de distribuição do seu código e preserve as licenças das dependências ao preparar uma publicação.

## Diagnóstico rápido

| Sintoma | Verificação |
| --- | --- |
| Roda não dispara | Hotkeys ativas, gatilho correto, foco do cliente e nível de elevação. |
| A tecla é enviada, mas o jogo não reage | Binding no cliente, contexto do chat e intervalos de envio. |
| Troca chama o slot errado | Sincronize o slot, remova atalhos repetidos e confira a lista efetiva. |
| Cursor vai ao lugar errado | Revise posições, resolução e escala; confira coordenadas no log. |
| Revive não ocorre | Confira o alvo visual, a tecla configurada e os avisos no log. |
| Macro dispara várias vezes | Aumente a trava da roda em Configurações. |

## Organização

`app/gui/` contém a interface; `app/models/`, configurações e perfis; `app/services/`, execução, hooks, detecção de janela e análise da barra do time; `app/utils/`, arquivos, logs e elevação. Os testes ficam na raiz. Configurações e logs são dados locais, fora do repositório.
