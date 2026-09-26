# Teste da troca de Pokémon (switch) — PXG

Data: 26/09/2026 (America/Sao_Paulo).
Ambiente: Windows/PowerShell, `.venv/Scripts/python.exe`, Python 3.12.10.

## Resultado

O laço completo passou: doze giros consecutivos, sincronizados inicialmente em 1, geraram **Ctrl+2, Ctrl+3, Ctrl+4, Ctrl+5, Ctrl+6, Ctrl+1, Ctrl+2, Ctrl+3, Ctrl+4, Ctrl+5, Ctrl+6, Ctrl+1**. O ciclo continuou após o 6 nas duas voltas, terminando no slot 1. As recusas registraram seus motivos. A validação da interface pela suíte existente ficou incompleta por erro de Tcl/Tk.

## Método e escopo

Os cenários adicionais foram executados por um script em memória, passado pela entrada padrão a `.\.venv\Scripts\python.exe -B -`, sem criar arquivo de teste. Foi reutilizado o `setUp` de `RotationTests`, com `AppController.__new__`, perfil PXG em memória, `FakeCombo`, foco simulado e persistência falsa. Foi acrescentado apenas à instância do fake o atributo `current = 'Macro simulada'`, exigido pelo log de recusa por execução em andamento.

A macro foi configurada com `switch=True`, gatilho `wheel_down` e etapas `Ctrl+N`; a rotação com revive foi desativada. Cada giro chamou o callback retornado por `wheel_bindings()['wheel_down']`, que encaminha para `_switch_pokemon`. Cada ação foi registrada pelo fake, sem envio ao teclado. Após cada giro:

1. Verificou-se início aceito, macro de troca e exatamente uma ação.
2. Chamou-se `_on_macro_step(f'{action.label} (1/1)')` e verificou-se o slot atualizado.
3. Chamou-se `_on_macro_finish(f'{SWITCH_NAME} concluida')` e verificou-se alvo limpo e slot preservado.
4. Zerou-se `combo.running = False` antes do próximo giro.

Não houve ressincronização entre os doze giros. O botão foi exercitado chamando o método real `ComboPage._sync_rotation_slot` com widgets e notificações falsos. Os Ctrl+N manuais foram simulados pelos callbacks reais das bindings, sem instalar hooks. Nenhuma tecla real foi enviada e o jogo não foi aberto. Os testes existentes usam configurações temporárias; `-B` evita a gravação de bytecode. Nenhum código foi corrigido.

## Cenários

Nas sequências abaixo, cada número representa `Ctrl+N`. “OK” nas limitações significa que o comportamento foi reproduzido, não que seja desejável.

| Cenário | Esperado | Obtido | OK |
|---|---|---|---|
| Lista 1,2,3,4,5,6; sincronizado em 1; 12 giros completos | 2,3,4,5,6,1,2,3,4,5,6,1 | Sequência exata; slot final 1; alvo limpo após cada conclusão | Sim |
| Lista completa, sem sincronização | Primeiro giro envia 1 | 1; slot passou de `None` para 1 | Sim |
| Sincronização direta por `set_pokemon_slot(4)` | Slot 4; próximo giro 5 | Slot 4; enviou 5 | Sim |
| Callback do botão Sincronizar, selecionando 3 | Slot 3; próximo giro 4 | Slot 3; uma notificação; enviou 4 | Sim, com UI falsa |
| Ctrl+1 até Ctrl+6 manuais | Cada callback atualiza o slot correspondente; próximo giro após 6 envia 1 | Todos os seis slots atualizados; enviou 1; bindings com `suppress=False` | Sim |
| Lista parcial 1,2,4; sincronizado em 1; 9 giros completos | 2,4,1,2,4,1,2,4,1 | Sequência exata | Sim |
| Lista parcial 1,2,4; slot atual 6 fora da lista | Próximo giro envia 1 | 1 | Sim |
| Hotkeys desativadas | Retorna `False`, sem ações e com motivo no log | Recusa e log de hotkeys desativadas | Sim |
| Macro em execução | Retorna `False`, sem ações e com motivo no log | Recusa e log identificando `Macro simulada` em execução | Sim |
| Jogo fora de foco | Retorna `False`, sem ações e com motivo no log | Recusa e log de janela fora do primeiro plano | Sim |
| Lista com um só atalho: 4; sincronizado em 4 | Limitação: percorre os seis | 5,6,1,2,3,4 | Sim, limitação confirmada |
| Atalho repetido: lista 1,2,2,4; sincronizado em 1 | Limitação: prende o ciclo no 2 | 2,2,2,2,2,2; não alcançou 4 | Sim, limitação confirmada |
| Suíte `test_rotation test_navigation test_game_profiles` | 18 testes aprovados | 15 aprovados e 3 erros de Tcl/Tk | Não |
| `selfcheck.py` | Todas as checagens aprovadas | 22/22 aprovadas | Sim |

As três recusas foram verificadas com `assertLogs('app.services.controller', level='INFO')`, incluindo retorno `False`, ausência de ações, slot 1 preservado e alvo ainda `None`. Mensagens capturadas:

```text
INFO:app.services.controller:Troca ignorada: hotkeys desativadas ou em edicao
INFO:app.services.controller:Troca ignorada: macro 'Macro simulada' ainda em execucao
INFO:app.services.controller:Troca ignorada: janela do jogo nao esta em primeiro plano
```

## Saída resumida dos testes

```text
> .\.venv\Scripts\python.exe -B -m unittest test_rotation test_navigation test_game_profiles
Ran 18 tests in 0.460s
FAILED (errors=3)
Código de saída: 1

> .\.venv\Scripts\python.exe -B selfcheck.py
22/22 checagens passaram
Código de saída: 0

> script adicional pela entrada padrão: .\.venv\Scripts\python.exe -B -
Ran 22 tests in 0.336s
OK
Código de saída: 0
```

O script adicional executou sete testes novos (incluindo três subcenários de recusa) e, pela descoberta do `unittest`, também os 15 testes da classe `RotationTests` importada. Portanto, não foram 22 cenários adicionais independentes.

Na suíte solicitada, os 15 testes de `test_rotation` passaram. Os erros ocorreram em:

- `test_navigation.NavigationTest.test_navigation`;
- `test_navigation.NavigationTest.test_rotation_macro_can_be_selected_and_synced`;
- `test_game_profiles.GameProfilesTest.test_legacy_migration_switch_and_reload`.

Todos falharam ao construir `MainWindow`, com `_tkinter.TclError: Can't find a usable init.tcl`, apontando para `C:\Users\renna\AppData\Local\Programs\Python\Python312\tcl\tcl8.6`. Isso impediu validar as etapas de interface desses testes. No teste de perfis, as verificações anteriores à construção da janela foram executadas sem erro, mas o teste completo não passou. O ambiente não foi reparado e os testes não foram alterados.

## Limitações conhecidas

- **Lista com um só atalho percorre os seis slots.** Uma lista contendo apenas Ctrl+4, sincronizada em 4, gerou 5,6,1,2,3,4. O código usa os seis slots quando encontra menos de dois atalhos reconhecidos.
- **Atalho repetido na lista prende o ciclo.** Com 1,2,2,4, o resultado foi seis envios de Ctrl+2. A busca pela primeira ocorrência do slot atual volta sempre à mesma posição e impede avançar ao 4.

## O que ainda depende de teste dentro do jogo

- Confirmar que o PXG recebe cada Ctrl+N e efetivamente coloca o Pokémon esperado em campo durante duas voltas completas.
- Validar o scroll físico, debounce, velocidade de giros e retomada após uma tentativa recusada enquanto a macro ainda executa.
- Confirmar o acompanhamento dos Ctrl+N físicos e a sincronização visual com o Pokémon realmente ativo, inclusive se o jogo recusar uma troca.
- Verificar foco real da janela, permissões de execução e eventuais interferências de outros atalhos.

Os fakes comprovam a lógica e a sequência de callbacks, mas não a entrega ao cliente, temporização real ou condições concorrentes. A interface real do botão Sincronizar também precisa ser retestada em um ambiente com Tcl/Tk funcional.

## Rodada 2 — Ctrl+1 e intervalo da roda

Executada em 26/09/2026 com `.venv/Scripts/python.exe -B -`, usando script em memória, fakes e `unittest.mock.patch`. Nenhuma tecla real foi enviada, nenhum hook foi instalado e nenhum código ou configuração foi corrigido. Todas as asserções desta rodada passaram; o processo terminou com código 0. As alterações preexistentes no projeto foram preservadas.

**1. Envio e interpretação de Ctrl+1 a Ctrl+6.** Em `app/services/action_executor.py`, `keyboard_module()` foi substituído por um fake que registra `press` e `release`; `_sleep_ms` registrou a espera sem dormir. `tap('ctrl+1', 30)` e `tap('ctrl+2', 30)` retornaram `True`, com estas chamadas:

```text
Ctrl+1: press('ctrl+1'), sleep_ms(30), release('ctrl+1')
Ctrl+2: press('ctrl+2'), sleep_ms(30), release('ctrl+2')
```

A mesma asserção passou para Ctrl+3, Ctrl+4, Ctrl+5 e Ctrl+6: só muda a tecla. O fake verifica as chamadas do executor, não eventos físicos gerados pela biblioteca. As funções reais `keyboard.key_to_scan_codes` e `keyboard.parse_hotkey` foram consultadas, sem envio nem registro de atalhos:

| Tecla | `key_to_scan_codes` | `parse_hotkey` |
|---|---|---|
| `1` | `(2, 79)` | `(((2, 79),),)` |
| `2` | `(3, 80)` | `(((3, 80),),)` |
| `3` | `(4, 81)` | `(((4, 81),),)` |
| `4` | `(5, 75)` | `(((5, 75),),)` |
| `5` | `(6, 76)` | `(((6, 76),),)` |
| `6` | `(7, 77)` | `(((7, 77),),)` |

Também foi consultado `parse_hotkey('ctrl+N')`: todos retornaram a estrutura `(((29, 57629, 57373), (códigos de N)),)`. Não houve falha de resolução nem estrutura especial para 1; os códigos diferentes correspondem às teclas diferentes.

**2. Bindings efetivas.** O perfil real `dist/PKA_PXG_Hotkeys/config/profiles/pxg.json` foi carregado com `Profile.from_dict`. Reutilizou-se o `setUp` de `RotationTests` de `test_rotation.py` (controller criado com `__new__`, `FakeCombo`, foco e persistência falsos), substituindo o perfil e as configurações em memória. `AppController.build_bindings()` foi chamado separadamente com `config/settings.json` e `dist/PKA_PXG_Hotkeys/config/settings.json`, sobrepondo os campos de `game_settings.PXG` aos globais. As duas execuções produziram exatamente as mesmas 18 bindings e nenhuma binding ignorada:

| Hotkey | `suppress` |
|---|---|
| `ctrl+alt+1` | `True` |
| `ctrl+alt+2` | `True` |
| `ctrl+alt+3` | `True` |
| `ctrl+alt+4` | `True` |
| `ctrl+alt+5` | `True` |
| `ctrl+alt+6` | `True` |
| `ctrl+alt+7` | `True` |
| `ctrl+alt+8` | `True` |
| `ctrl+alt+9` | `True` |
| `ctrl+alt+f` | `True` |
| `ctrl+alt+r` | `True` |
| `ctrl+1` | `False` |
| `ctrl+2` | `False` |
| `ctrl+3` | `False` |
| `ctrl+4` | `False` |
| `ctrl+5` | `False` |
| `ctrl+6` | `False` |
| `esc` | `False` |

Existe uma binding que observa Ctrl+1 para acompanhar o slot, mas ela não o suprime; é igual às de Ctrl+2..6. `ctrl+alt+1` exige também Alt. A configuração `suppress_hotkeys=True` não muda o `False` explícito dos observadores. A emergência é `pause`, registrada separadamente com `suppress=False` no código, fora de `build_bindings`. `wheel_bindings()` retornou `mouse_x2`, `mouse_x1` e `wheel_up`; esses gatilhos não suprimem eventos. Nenhum registro real foi executado.

**3. Debounce da roda.** O arquivo distribuído contém `wheel_debounce_ms=250`, tanto globalmente quanto em `game_settings.PXG`; `config/settings.json` mantém 80 ms globalmente. Foram criados eventos falsos `WheelEvent(delta=1)`, substituído `_mouse` e controlado `time.monotonic`. Os callbacks foram colocados diretamente em `_callbacks`, sem chamar `bind`. Cada cenário usou um `WheelManager` novo e chamou `_on_event` nos cinco instantes pedidos, relativos à base monotônica de 100 segundos:

| Debounce | Eventos em ms | Disparos em ms | Total |
|---|---|---|---|
| 250 ms (novo) | 0, 50, 113, 260, 600 | 0, 260, 600 | **3** |
| 80 ms (antigo) | 0, 50, 113, 260, 600 | 0, 113, 260, 600 | **4** |

O intervalo é contado desde o último disparo aceito; eventos descartados não renovam a janela. São contagens de callbacks, não garantias de trocas aceitas pelo controller ou pelo jogo.

Foi testada também a condição artificial de `monotonic()` começar exatamente em zero. Como `_last_fired.get(trigger, 0.0)` usa zero como valor inicial, o evento em 0 é descartado: com 250 ms há **2** disparos (260, 600); com 80 ms há **3** (113, 260, 600). Essa particularidade foi registrada sem corrigir o código; a base positiva acima representa os tempos relativos de eventos durante a execução normal.

**4. Log real e intervalos.** Foi lido o trecho de `dist/PKA_PXG_Hotkeys/logs/app.log` da linha 776 (`12:50:00.077`) até o fim (`12:59:13.477`), totalizando 705 linhas. A seleção inicial apenas por horário também incluía entradas antigas das 17h; o recorte foi corrigido para começar na primeira linha das 12:50. Os 43 registros de `Troca iniciada` e seus 42 intervalos permaneceram iguais. A tabela abaixo usa diferenças inteiras em milissegundos entre esses registros consecutivos; não inclui `Rotação iniciada` nem `Troca ignorada`.

| De | Para | Ctrl+N | Intervalo (ms) | < 250 ms |
|---|---|---|---|---|
| 12:50:11.462 | 12:50:13.071 | 1 -> 2 | 1609 | - |
| 12:50:13.071 | 12:50:14.292 | 2 -> 3 | 1221 | - |
| 12:50:14.292 | 12:50:14.405 | 3 -> 4 | 113 | **Sim** |
| 12:50:14.405 | 12:50:16.167 | 4 -> 5 | 1762 | - |
| 12:50:16.167 | 12:50:18.207 | 5 -> 6 | 2040 | - |
| 12:50:18.207 | 12:50:19.900 | 6 -> 1 | 1693 | - |
| 12:50:19.900 | 12:50:21.414 | 1 -> 2 | 1514 | - |
| 12:50:21.414 | 12:50:23.412 | 2 -> 3 | 1998 | - |
| 12:50:23.412 | 12:50:25.216 | 3 -> 4 | 1804 | - |
| 12:50:25.216 | 12:50:26.881 | 4 -> 5 | 1665 | - |
| 12:50:26.881 | 12:50:28.449 | 5 -> 6 | 1568 | - |
| 12:50:28.449 | 12:50:29.985 | 6 -> 1 | 1536 | - |
| 12:50:29.985 | 12:51:13.115 | 1 -> 2 | 43130 | - |
| 12:51:13.115 | 12:51:14.869 | 2 -> 3 | 1754 | - |
| 12:51:14.869 | 12:51:16.422 | 3 -> 4 | 1553 | - |
| 12:51:16.422 | 12:51:17.966 | 4 -> 5 | 1544 | - |
| 12:51:17.966 | 12:51:19.557 | 5 -> 6 | 1591 | - |
| 12:51:19.557 | 12:51:21.059 | 6 -> 1 | 1502 | - |
| 12:51:21.059 | 12:52:14.317 | 1 -> 3 | 53258 | - |
| 12:52:14.317 | 12:52:15.537 | 3 -> 4 | 1220 | - |
| 12:52:15.537 | 12:52:16.731 | 4 -> 5 | 1194 | - |
| 12:52:16.731 | 12:52:16.842 | 5 -> 6 | 111 | **Sim** |
| 12:52:16.842 | 12:52:18.724 | 6 -> 1 | 1882 | - |
| 12:52:18.724 | 12:52:22.397 | 1 -> 2 | 3673 | - |
| 12:52:22.397 | 12:52:23.323 | 2 -> 3 | 926 | - |
| 12:52:23.323 | 12:52:24.698 | 3 -> 4 | 1375 | - |
| 12:52:24.698 | 12:52:26.066 | 4 -> 5 | 1368 | - |
| 12:52:26.066 | 12:52:26.600 | 5 -> 6 | 534 | - |
| 12:52:26.600 | 12:52:27.841 | 6 -> 1 | 1241 | - |
| 12:52:27.841 | 12:52:29.192 | 1 -> 2 | 1351 | - |
| 12:52:29.192 | 12:52:30.838 | 2 -> 3 | 1646 | - |
| 12:52:30.838 | 12:52:32.481 | 3 -> 4 | 1643 | - |
| 12:52:32.481 | 12:52:34.250 | 4 -> 5 | 1769 | - |
| 12:52:34.250 | 12:53:00.818 | 5 -> 6 | 26568 | - |
| 12:53:00.818 | 12:53:25.104 | 6 -> 1 | 24286 | - |
| 12:53:25.104 | 12:53:25.212 | 1 -> 2 | 108 | **Sim** |
| 12:53:25.212 | 12:53:25.643 | 2 -> 3 | 431 | - |
| 12:53:25.643 | 12:53:40.909 | 3 -> 5 | 15266 | - |
| 12:53:40.909 | 12:53:41.208 | 5 -> 6 | 299 | - |
| 12:53:41.208 | 12:53:45.029 | 6 -> 1 | 3821 | - |
| 12:53:45.029 | 12:59:05.899 | 1 -> 4 | 320870 | - |
| 12:59:05.899 | 12:59:06.135 | 4 -> 5 | 236 | **Sim** |

Os quatro intervalos abaixo de 250 ms são **113, 111, 108 e 236 ms**. São compatíveis com a janela antiga de 80 ms; o valor atual no JSON não comprova qual valor estava carregado quando o log foi produzido. Esses intervalos medem inícios de trocas, não diretamente eventos da roda.

O log registra Ctrl+1 em oito inícios de troca: `12:50:11.462`, `12:50:19.900`, `12:50:29.985`, `12:51:21.059`, `12:52:18.724`, `12:52:27.841`, `12:53:25.104` e `12:53:45.029`. Em todas as sete passagens de Ctrl+6 para o próximo registro de troca, o destino é Ctrl+1. Todos esses Ctrl+1 têm registros de pressionar e soltar, com toque configurado de 30 ms. Há ainda um Ctrl+1 da macro de rotação às `12:52:09.977`, solto às `12:52:10.013`. Às `12:53:25.212`, Ctrl+2 começa somente 108 ms após a troca para Ctrl+1, o que merece observação no teste dentro do jogo.

**Conclusão.** Não foi encontrada diferença de tratamento do lado do app entre Ctrl+1 e Ctrl+2..6, além dos códigos próprios de cada tecla: envio, espera e bindings são equivalentes. O app registra o retorno ao 1 após o 6. Com essas evidências, a causa do Pokémon 1 não voltar fica no jogo e precisa do teste manual: **com o Pokémon 6 em campo e o PXG em foco, pressionar Ctrl+1 no teclado e verificar se o Pokémon 1 entra**. Os testes com fakes e o log não comprovam que o cliente recebeu ou aceitou a troca, nem identificam a condição interna do jogo. O teste manual não foi realizado nesta rodada.


## Rodada 3 — Ctrl+1 com folga do modificador

Executada em 26/09/2026 com `.venv/Scripts/python.exe`. **Contexto informado pelo usuário:** no PXG, Ctrl+1 apertado à mão chama o Pokémon 1, mas o Ctrl+1 da macro não, inclusive sincronizando em 6 com o Pokémon 4 em campo. Ctrl+2..6 enviados pela macro funcionam. Isso complementa a rodada anterior: a falha não pode ser atribuída somente à lógica interna do jogo; a diferença entre entrada manual e sintética continua em investigação. A hipótese de o cliente ler apenas `1` por falta de folga não foi comprovada pelos mocks.

**Mudança sob teste e método.** O `tap()` atual de `app/services/action_executor.py` separa a combinação, pressiona cada modificador com `MODIFIER_LEAD_MS = 40` ms de espera, pressiona a tecla final, espera `hold_ms`, solta a tecla e solta os modificadores em ordem inversa, esperando 40 ms antes de cada liberação. A folga é **por modificador**, não uma espera única para todos. Teclas únicas seguem o caminho anterior. Foram executados scripts em memória pela entrada padrão (`.\.venv\Scripts\python.exe -B -`), com `keyboard_module()` substituído por teclado falso, eventos registrados e conjunto de teclas pressionadas. Para sequências determinísticas, `_sleep_ms` avançou um relógio falso; na medição de duração, as esperas foram reais. Nenhuma tecla real foi enviada e nenhum hook foi instalado. Somente este documento foi complementado; nenhum código foi corrigido.

**1. Ordem e tempos dos eventos.** Todos os casos abaixo usaram `hold_ms=30`. Os tempos são milissegundos relativos ao início, calculados pelo relógio falso; `↓` significa `press` e `↑` significa `release`. Entre eventos, as esperas registradas foram exatamente as indicadas pela diferença de tempo.

| Entrada | Eventos observados | Esperas, em ordem | Retorno / total programado |
|---|---|---|---|
| `ctrl+1` | 0: ↓ctrl; 40: ↓1; 70: ↑1; 110: ↑ctrl | 40, 30, 40 ms | `True` / 110 ms |
| `ctrl+6` | 0: ↓ctrl; 40: ↓6; 70: ↑6; 110: ↑ctrl | 40, 30, 40 ms | `True` / 110 ms |
| `ctrl+alt+f` | 0: ↓ctrl; 40: ↓alt; 80: ↓f; 110: ↑f; 150: ↑alt; 190: ↑ctrl | 40, 40, 30, 40, 40 ms | `True` / 190 ms |
| `q` | 0: ↓q; 30: ↑q | 30 ms | `True` / 30 ms |
| `ctrl+` | 0: ↓`ctrl+`; 30: ↑`ctrl+` | 30 ms | `True` / 30 ms, fake permissivo |
| `+` | 0: ↓`+`; 30: ↑`+` | 30 ms | `True` / 30 ms, fake permissivo |

As asserções de ordem, duração, retorno, ausência de teclas presas e `busy=False` ao final passaram. Ctrl+1 e Ctrl+6 recebem tratamento idêntico, exceto pela tecla final. Para `ctrl+` e `+`, partes vazias fazem o código encaminhar a string inteira à biblioteca, como uma tecla única: **não há rejeição local da entrada malformada**. O retorno positivo do fake não comprova aceitação nem interpretação correta pela biblioteca real, especialmente para a tecla literal `+`.

**2. Exceção no segundo `press` e limpeza.** O fake lançou `RuntimeError` na segunda chamada de `press`, antes de adicionar a segunda tecla ao conjunto de pressionadas. “Segundo evento” aqui significa a segunda tentativa de pressionar; existe uma espera de 40 ms entre as duas tentativas.

| Entrada | Ponto da falha, em 40 ms | Chamadas do `except`, em ordem, sem novas esperas | Resultado |
|---|---|---|---|
| `ctrl+1` | `press('1')`, após Ctrl pressionado | `release('1')`, `release('ctrl')` | `False`; nenhuma tecla presa |
| `ctrl+6` | `press('6')`, após Ctrl pressionado | `release('6')`, `release('ctrl')` | `False`; nenhuma tecla presa |
| `ctrl+alt+f` | `press('alt')`, após Ctrl pressionado | `release('f')`, `release('alt')`, `release('ctrl')` | `False`; nenhuma tecla presa |

O `except` tenta soltar **todas** as partes em ordem inversa, inclusive partes que não chegaram a ser pressionadas. O lock foi liberado em todos esses casos.

**Falha adicional reproduzida:** repetindo o erro em `press('1')` e fazendo também `release('1')` levantar exceção, o laço de recuperação para imediatamente. `release('ctrl')` não é chamado; o fake termina com `{'ctrl'}` pressionado, embora `tap()` retorne `False` e `busy` volte a `False`. O `try/except` envolve o laço inteiro, portanto não garante a liberação dos modificadores se uma liberação anterior falhar. Esse risco foi registrado sem correção. A recuperação também não distingue modificadores que o usuário já estivesse segurando fisicamente; isso não foi simulado.

**3. Duração de uma troca.** `_switch_pokemon()` cria uma única ação Ctrl+N com `DEFAULT_HOLD_MS=30`; o `ComboManager` não aplica `delay_ms` após a última ação. O orçamento de espera passa de 30 para **110 ms**, acréscimo de **80 ms**. Com dois modificadores, passa de 30 para 190 ms. A fórmula para combinações separadas normalmente é `max(0, hold_ms) + 80 × quantidade de modificadores`.

Foram medidas dez execuções de uma macro de uma etapa Ctrl+1 pelo `ComboManager` real, com `ActionExecutor` real, teclado falso e esperas reais. O cronômetro cobriu `start()` até o retorno de `wait(5)`, incluindo a thread. Para comparação, outras dez execuções substituíram apenas o método da instância por uma reconstrução em memória do caminho antigo: lock, `press(key)`, espera de 30 ms e `release(key)`.

| Caminho | Mínimo | Mediana | Máximo |
|---|---|---|---|
| Atual | 111,44 ms | **111,91 ms** | 112,26 ms |
| Antigo reconstruído com fake | 30,91 ms | **31,02 ms** | 31,32 ms |

A diferença entre medianas foi 80,89 ms. Os **~37 ms anteriores** são a referência informada, não uma medida reproduzida nesta rodada. Mantendo aproximadamente o mesmo overhead daquela referência, a estimativa atual seria **~117 ms** (37 + 80). Os ~112 ms medidos usam fake e não incluem custos reais da biblioteca, entrega ao cliente ou resposta do jogo; tampouco medem todo o callback do controller. Não há contradição entre esses números nem garantia de duração exata no Windows.

**4. Suítes solicitadas.** Ambas foram executadas sem alterar os testes:

```text
> .\.venv\Scripts\python.exe -B -m unittest test_rotation
Ran 16 tests in 0.395s
OK
Código de saída: 0

> .\.venv\Scripts\python.exe -B selfcheck.py
22/22 checagens passaram
Código de saída: 0

> script em memória: .\.venv\Scripts\python.exe -B -
All assertions passed
Código de saída: 0
```

Os logs de erro de envio do script adicional foram provocados deliberadamente pelas exceções descritas acima. Todas as asserções passaram, inclusive a que comprova Ctrl preso quando a limpeza falha; isso **não** significa que esse comportamento seja seguro ou desejável. Esta rodada não reexecutou os testes de interface que falharam por Tcl/Tk anteriormente.

**5. Revisão dos demais usos de `tap()`.** Foram revisados `ActionExecutor.run_action`, `AppController._run_skill`, a montagem de ações no controller e `ComboManager._execute`/`_run`.

- **Skills e macros de ataque:** teclas únicas mantêm a sequência e o tempo programado anteriores. Qualquer skill ou etapa configurada com combinação ganha 80 ms por modificador; isso pode alterar o ritmo dos ataques e os intervalos efetivos entre etapas. Os delays configurados continuam sendo aplicados depois da execução da etapa, quando há uma próxima etapa.
- **Revive `q`:** o teste confirmou 30 ms, sem folga adicional. O caminho de clique/restauração do ponteiro não foi alterado por essa mudança. Na rotação que combina troca e revive, a troca anterior ao revive fica 80 ms mais longa; a sequência completa, portanto, também aumenta.
- **Comandos:** ações em modo comando usam `send_command()`, que chama `keyboard.send`/`write` diretamente. Não passam por `tap()`, inclusive o fechamento de chat com `ctrl+e`, que não recebe a nova folga. Já ações ofensivas/defensivas configuradas como teclas seguem `tap()`; `r` e `e` únicas mantêm o comportamento. O selfcheck de fechamento do chat passou.
- **Concorrência e cancelamento:** o lock permanece adquirido durante todas as novas esperas. A janela em que o executor está ocupado e a macro de troca está em execução aumenta; novos gatilhos podem ser recusados nesse período. O cancelamento do `ComboManager` é verificado entre etapas e nos delays, mas não interrompe as esperas internas de `tap()`; uma combinação em andamento precisa terminar ou falhar antes de liberar a execução.
- **Entradas e liberação:** o parser separa por `+` e trata todas as partes anteriores à última como modificadores, sem validar se realmente são Ctrl/Alt/Shift etc. Combinações não convencionais merecem teste específico. Entradas malformadas e falhas durante a limpeza têm as limitações reproduzidas acima. Modificadores ficam pressionados por mais tempo, ampliando a possibilidade de interagir com outras entradas físicas.

**Conclusão desta rodada.** A ordem e a folga de Ctrl+1 foram confirmadas no executor com teclado falso, e as duas suítes solicitadas passaram. Foi reproduzida uma limitação de recuperação que pode deixar Ctrl preso se `release` também falhar. **A confirmação final depende do jogo:** repetir o cenário informado (Pokémon 4 em campo, sincronização em 6 e próximo envio Ctrl+1), verificar se o Pokémon 1 entra e conferir que Ctrl+2..6, revive e ataques continuam funcionando. Os mocks não demonstram que 40 ms resolvem a falha do PXG.
## Rodada 4 — Revive clicando no retrato grande

Executada em 26/09/2026 com `.venv/Scripts/python.exe -B`. **Contexto informado pelo usuário a partir dos prints:** no PXG, o Pokémon em campo ocupa sempre o retrato grande no topo da barra; os retratos pequenos se reordenam a cada troca, mas Ctrl+N continua chamando o mesmo Pokémon. Por isso, o alvo do revive passa a ser o retrato grande, independentemente da posição dos pequenos. Esta rodada não valida visualmente o cliente do jogo.

**Mudança e método.** `Profile.active_portrait` guarda um par relativo à área útil do jogo. Foi carregado, somente para leitura, `dist/PKA_PXG_Hotkeys/config/profiles/pxg.json`: `active_portrait=[48, 63]`, tecla de revive `q` e `delay_ms=300` na primeira etapa da macro de revive. `AppController._next_slot` fornece a fila comum à troca e ao revive; sem sincronização, escolhe o primeiro da fila. A fila usa os Ctrl+N da macro de troca habilitada; com menos de dois atalhos reconhecidos, usa 1..6.

Os cenários adicionais rodaram em um script em memória, pela entrada padrão de `.\.venv\Scripts\python.exe -B -`, reutilizando o `setUp` de `RotationTests`, com controller sem inicialização real, `FakeCombo`, foco e origem da janela falsos e perfil carregado em memória. Para executar as ações, foram usados `ComboManager._run` e `ActionExecutor` reais, com teclado e mouse falsos; as esperas foram registradas sem dormir. Nenhuma tecla ou clique real foi enviado, nenhum hook foi instalado e nenhum código ou configuração foi corrigido. As alterações preexistentes foram preservadas; somente este documento foi complementado.

**1. Sequência, coordenadas e devolução no caminho de sucesso.** Com origem falsa da área útil em `(1000, 500)` e sem sincronização, `_rotate_pokemon()` retornou `True` e gerou:

| Etapa | Resultado observado |
|---|---|
| Puxar o próximo | `Ctrl+1`, `hold_ms=30`, `delay_ms=300` |
| Apontar o Pokémon em campo | Clique em `(1048, 563)`, soma de `(1000, 500)` com `(48, 63)`, com `restore=False` |
| Reviver | `q`, `hold_ms=30`, com o ponteiro ainda em `(1048, 563)` |
| Devolver ponteiro | Ação `pointer_home`, retornando à posição falsa inicial `(800, 900)` |

A ordem dos tipos foi exatamente `key → click → key → pointer_home`. Na execução real do gerenciador com entradas falsas, a espera de `0,3 s` ocorreu depois de soltar Ctrl e antes de mover o mouse. Os 300 ms vêm de `delay_ms` da etapa de revive, não são a duração total da macro. O executor também registrou as folgas de Ctrl (40 + 30 + 40 ms), duas esperas de 40 ms no clique e o toque de 30 ms de `q`. No sucesso, houve quatro notificações de etapa, término `concluida`, ponteiro devolvido e `_pointer_home=None`.

**2. Janela não localizada.** Mantendo o foco falso como verdadeiro, mas retornando `None` em `game_client_origin()`, a rotação foi aceita e gerou somente `Ctrl+1 → q`, sem clique nem ação de retorno. Foram capturados dois avisos:

```text
Não foi possível localizar a janela do jogo para clicar
Revive sem clique: posição do retrato grande não configurada
```

O segundo aviso é impreciso nesse cenário: o retrato estava configurado, mas a origem da janela não foi localizada. A macro continua enviando as teclas; isso não garante um alvo válido para o revive. Esse cenário isola a falta de origem, sem acionar a recusa separada por falta de foco.

**3. Perfil sem o campo e com lixo.** Foram testados campo ausente, `null` e oito valores inválidos: `"lixo"`, `17`, `{}`, `[]`, `[48]`, `[48, 63, 1]`, `["x", 63]` e `[null, 63]`. Em todos esses casos, `Profile.from_dict` normalizou `active_portrait` para `None`; a rotação retornou `True`, produziu apenas `Ctrl+1 → q` e emitiu o aviso de revive sem clique. A validação foi exercitada no carregamento do perfil, não por atribuição direta de dados inválidos ao atributo. O par de strings numéricas `["48", "63"]` foi aceito e convertido para `(48, 63)`; portanto, nem todo valor com strings é rejeitado.

**4. Ida e volta do perfil.** Passaram as asserções de `from_dict → to_dict → from_dict` para `[48, 63]`, `null` e `[0, 0]`, incluindo igualdade do dicionário completo após a segunda serialização. O par é tupla em memória e lista na saída; a ausência normalizada é serializada como `null`. Nenhum perfil foi salvo em disco.

**5. Troca e revive compartilham o slot.** Começando sincronizado em 1, foram alternadas troca, revive, troca e revive, notificando as etapas e o término de cada macro antes da próxima chamada. Os primeiros envios foram exatamente **Ctrl+2, Ctrl+3, Ctrl+4 e Ctrl+5**: a troca 1→2 fez o revive seguinte puxar 3. Também foi verificada a fila parcial 1,2,4: sem sincronização, `_next_slot(None)` retornou 1; sincronizado em 2, o revive puxou 4. O slot acompanhado é atualizado pelo callback da etapa de puxar, sem comprovar que o jogo aceitou a troca.

**6. Falha na tecla do revive: o ponteiro não é devolvido.** O teclado falso lançou `RuntimeError` em `press('q')`, depois do clique bem-sucedido. O `ActionExecutor.tap` tentou soltar `q` e retornou `False`. O `ComboManager` interrompeu a macro na etapa **3/4**, notificou apenas as duas etapas anteriores e terminou como `interrompida por erro`.

O mouse falso permaneceu em **`(1048, 563)`, sobre o retrato**, e `_pointer_home` continuou guardando `(800, 900)`. A etapa `pointer_home` não foi executada. O `finally` de `ComboManager._run` limpa o estado de execução e notifica o término, mas não restaura o mouse; o callback de término do controller também não o restaura. **A devolução está confirmada apenas no caminho de sucesso; não é garantida quando o revive falha.** A asserção que reproduz essa falha passou, o que não significa que o comportamento seja desejável. Nenhuma correção foi feita.

**7. Suítes e resultado da execução.** Os comandos solicitados rodaram sem alteração dos testes:

```text
> .\.venv\Scripts\python.exe -B -m unittest test_rotation
Ran 19 tests in 0.353s
OK
Código de saída: 0

> .\.venv\Scripts\python.exe -B selfcheck.py
22/22 checagens passaram
Código de saída: 0

> script adicional em memória: .\.venv\Scripts\python.exe -B -
ALL ADDITIONAL ASSERTIONS PASSED
Código de saída: 0
```

O script adicional executou asserções diretas, sem descoberta automática dos testes importados. Os erros de envio de `q` e da etapa 3/4 nesse script foram provocados deliberadamente. As suítes passaram, mas permanece a falha reproduzida de devolução do ponteiro. Os fakes confirmam sequência, coordenadas calculadas e tratamento dos casos exercitados; não confirmam entrega ao PXG, alvo efetivamente revivido, suficiência dos 300 ms nem adequação de `[48, 63]` em outra resolução ou disposição da interface. Esses pontos ainda dependem de teste dentro do jogo.
