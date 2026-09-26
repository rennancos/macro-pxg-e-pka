# Revisão de segurança — 26/09/2026

## Resultado

**Há uma pendência confirmada antes de recomendar distribuição pública:** uma macro pode continuar enviando entradas depois que outra janela ganha foco (SEC-001). Não interpretar os testes aprovados ou a ausência de CVEs como certificação de segurança do programa.

Revisão local do código de trabalho baseado no commit `0ba3b97`, com alterações ainda não commitadas e desenvolvimento simultâneo. O resultado cobre o estado lido e testado nesta sessão, não um executável publicado nem alterações posteriores. Nenhum pacote foi publicado ou enviado a serviço de análise de binários.

## Evidências

| Verificação | Resultado |
| --- | --- |
| Testes `test_security test_rotation test_navigation test_game_profiles` | 31 executados: 30 aprovados e 1 falha esperada, SEC-001. |
| `selfcheck.py` | 22/22 aprovadas. |
| Bandit 1.9.4 em `app/` e `main.py` | 13 alertas baixos; nenhum médio ou alto; não substitui revisão manual. |
| pip-audit 2.10.1, índice PyPI | 11 versões instaladas consultadas; nenhuma vulnerabilidade conhecida encontrada. |
| Busca por padrões de segredos nos 42 arquivos rastreados | Nenhuma correspondência; não é varredura completa do histórico ou detector universal. |
| Dados locais rastreados pelo Git | Nenhum perfil pessoal, log, build ou ambiente virtual encontrado nos caminhos verificados. |
| Regras do `.gitignore` | Verificadas com `git check-ignore`, incluindo backups de configurações, builds de teste, `.env`, certificados e relatórios locais. |

A suíte gráfica emitiu mensagens Tcl sobre callbacks pendentes depois de destruir janelas, mas terminou sem falhas inesperadas. O ambiente usou `TCL_LIBRARY` e `TK_LIBRARY` apontando para os recursos do build local existente. Não houve envio real de teclas ou cliques ao jogo.

As versões auditadas foram: altgraph 0.17.5, customtkinter 6.0.0, darkdetect 0.8.0, keyboard 0.13.5, mouse 0.7.1, packaging 26.3, pefile 2024.8.26, pyinstaller 6.22.3, pyinstaller-hooks-contrib 2026.7, pywin32-ctypes 0.2.3 e setuptools 84.0.0. A consulta usou o inventário instalado, incluindo dependências transitivas, com `--no-deps --disable-pip`; não resolveu novamente os intervalos de `requirements.txt`. Não certifica instalações futuras.

## Achados manuais

### SEC-001 — Entradas podem alcançar outra janela durante a macro

Prioridade: alta para distribuição. Confirmado por teste simulado, ainda sem correção nesta revisão.

O controlador verifica o foco no início. `ComboManager._run` executa as etapas seguintes sem uma nova guarda geral de foco, e `ActionExecutor` não recebe um verificador de foco. Se o usuário fizer Alt+Tab durante uma espera, uma tecla ou texto posterior pode chegar ao aplicativo que ficou em primeiro plano. O reconhecimento visual ter suas próprias consultas de janela não protege todas as macros e comandos.

Reprodução: `test_security.SecurityTests.test_known_gap_focus_loss_must_block_next_step` simula perda de foco após a primeira ação; observa envio da segunda mesmo assim. Está marcado como `expectedFailure` para explicitar uma deficiência conhecida, não como teste de proteção aprovado.

Correção recomendada: revalidar foco e estado de cancelamento nos pontos de envio, inclusive nas partes de um comando de chat, e abortar de forma controlada. Soltar teclas já pressionadas deve continuar permitido. Nenhuma consulta prévia elimina totalmente a corrida com a troca de foco do sistema; documentar esse limite e testar Alt+Tab no Windows após a correção.

### SEC-002 — Dados privados em configurações, logs e pacotes

Os logs registram os comandos configurados, nomes e coordenadas. Perfis podem conter caminhos locais e ações pessoais. As ferramentas de captura de gatilhos e os hooks escutam eventos globais; não é correto afirmar genericamente que não há captura de teclado. Não foi encontrado envio desses dados pela rede no código da aplicação revisado.

Mitigação aplicada: `.gitignore` cobre toda a configuração local, com exceção do marcador vazio, além de logs, backups, builds e materiais de auditoria. README explica o conteúdo dos registros e a preparação de um pacote limpo. Isso não remove dados de commits anteriores e não filtra ZIPs criados manualmente.

### SEC-003 — Revive visual é uma heurística experimental

`team_bar.py` lê regiões da tela usando GDI e escolhe uma barra com poucos pixels verdes. Não salva a imagem nem a envia pela rede nesse fluxo. Um erro de layout, captura ou classificação pode levar a clique/alvo incorreto. A captura não valida todos os retornos das APIs GDI, e múltiplas barras vazias não produzem necessariamente um alvo inequívoco.

Antes de distribuir esse recurso como confiável, validar falhas de captura, limites de coordenadas, múltiplos candidatos, resolução/escala e perda de foco. O fluxo sem calibração suficiente ainda envia revive sem clique; isso foi documentado, não alterado. O README anterior negava leitura de tela e foi corrigido.

### SEC-004 — Cancelamento durante um envio

As esperas entre etapas são canceláveis. Um `tap` ou `send_command` já iniciado pode continuar até retornar; o teste de cancelamento não demonstra parada instantânea dentro de um texto longo. Considerar guardas também no envio e limites razoáveis para duração/tamanho antes da distribuição.

### Empacotamento e privilégios

O build solicita administrador. A detecção do cliente consulta informações do processo e usa o nome do executável/classe, não valida a identidade criptográfica do cliente. Não foi encontrada leitura da memória do jogo, execução de comandos de shell fornecidos por perfil, desserialização via pickle ou comunicação de rede no código próprio examinado. Os perfis são JSON e seus nomes de arquivo são normalizados; foram testados exemplos de tentativa de escapar do diretório.

A aplicação elevada, suas DLLs, dependências e configurações precisam vir de uma origem confiável. Não foram executados antivírus, análise dinâmica do executável, revisão completa de bibliotecas de terceiros, testes de links simbólicos/junções nem auditoria de toda a história Git. O README deixou de recomendar exclusões de antivírus.

## Triagem do Bandit

- 9 alertas B110: exceções ignoradas em limpeza, hooks, interface e recuperação de envio. Podem ocultar falhas; não foram classificados como exploração comprovada nesta revisão.
- B404, B606, B607 e B603 em `logs_page.py`: abertura da pasta de logs, usando `os.startfile` no Windows e `xdg-open` no ramo alternativo. O caminho vem da aplicação e não há `shell=True`. O alerta de caminho parcial no ramo alternativo permanece registrado; o programa é voltado ao Windows.

## Reproduzir

```powershell
.\.venv\Scripts\python.exe -m unittest test_security test_rotation test_navigation test_game_profiles
.\.venv\Scripts\python.exe selfcheck.py
```

A auditoria automatizada foi instalada separadamente, sem alterar `requirements.txt` ou os pacotes da aplicação:

```powershell
.\.venv\Scripts\python.exe -m pip install --target .audit-tools pip-audit bandit
New-Item -ItemType Directory -Force .audit-results
.\.venv\Scripts\python.exe -m pip freeze --exclude-editable | Set-Content -Encoding utf8 .audit-results/installed.txt
$env:PYTHONPATH = (Resolve-Path .audit-tools).Path
.\.venv\Scripts\python.exe -m bandit -r app main.py -f json -o .audit-results/bandit.json
.\.venv\Scripts\python.exe -m pip_audit -r .audit-results/installed.txt --no-deps --disable-pip --cache-dir .audit-results/cache -f json -o .audit-results/pip-audit.json
Remove-Item Env:PYTHONPATH
```

Capture o inventário antes de definir `PYTHONPATH`, para não incluir as ferramentas de auditoria. A consulta de vulnerabilidades precisa de rede; os relatórios JSON são locais e ignorados pelo Git. O Bandit retorna código 1 quando há alertas, mesmo baixos.

## Antes de publicar uma versão

Resolver SEC-001 e repetir a revisão das etapas de envio e dos cenários visuais. Validar um build limpo com perfis novos, sem configurações pessoais, e verificar o pacote final com a proteção local habilitada. Definir a licença do projeto e preservar avisos das dependências. Repetir a consulta de vulnerabilidades para as versões efetivamente empacotadas. Esta revisão não produziu um pacote de distribuição aprovado.
