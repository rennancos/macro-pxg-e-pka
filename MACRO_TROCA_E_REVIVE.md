# Troca de Pokémon e Revive no PXG

Estado em 26/09/2026. O programa instalado em `dist\PKA_PXG_Hotkeys` já tem tudo o que está descrito aqui.

## Como o PXG se comporta

Estas regras vêm dos prints e dos testes feitos no jogo:

- **Cada `Ctrl+N` chama sempre o mesmo Pokémon.** Na equipe atual, `Ctrl+1` é o Steelix, `Ctrl+2` o Druddigon, `Ctrl+3` o roxo escuro, `Ctrl+4` o rosa, `Ctrl+5` o verde e `Ctrl+6` o azul.
- **O Pokémon em campo fica sempre no retrato grande do topo da barra do time.** Os outros cinco ficam nos retratos pequenos, e **a ordem deles muda a cada troca**.
- **O revive age no Pokémon que está sob o mouse.** Só apertar `Q` não revive nada. À mão, a sequência é: trocar de Pokémon, clicar no retrato pequeno do desmaiado e apertar `Q`.

## Troca de Pokémon (roda do mouse para cima)

Cada giro chama o próximo Pokémon da lista e, depois do último, volta ao primeiro.

- A lista são os passos da macro `trocar Pokémon`: `Ctrl+1` até `Ctrl+6`. Para pular um Pokémon, apague o atalho dele nos passos, pela interface.
- O programa acompanha qual Pokémon está em campo pelos `Ctrl+N` que você aperta no teclado. Se você trocar clicando num retrato, ajuste pelo botão **Sincronizar** da macro.
- Sem sincronizar, o primeiro giro chama o primeiro Pokémon da lista.
- Dois giros com menos de **250 ms** de diferença contam como um só. Isso evita que um giro da roda troque duas vezes.

## Revive (botão lateral do mouse)

1. `Ctrl+próximo` puxa o próximo Pokémon.
2. O programa espera **300 ms** para o desmaiado aparecer na fila dos retratos pequenos.
3. Ele lê as barras de vida verdes dos 5 retratos pequenos e escolhe a **vazia**, que é a do desmaiado.
4. Clica no retrato dele e deixa o mouse em cima.
5. Aperta `Q`.
6. Devolve o mouse para onde estava.

Se nenhuma barra estiver vazia, ou se a janela do jogo estiver coberta, a macro para antes do `Q`: não clica e não gasta o revive. Se algo der erro no meio, ou se você cancelar com ESC, o mouse volta mesmo assim.

## Onde ajustar

| O quê | Onde | Valor atual |
|---|---|---|
| Lista de Pokémon da troca | Passos da macro `trocar Pokémon` (interface) | `Ctrl+1` a `Ctrl+6` |
| Intervalo mínimo entre giros | `config\settings.json`, `wheel_debounce_ms` do PXG | 250 ms |
| Espera antes de procurar o desmaiado | Primeiro passo da macro `revive e trocar Pokémon`, `delay_ms` | 300 ms |
| Posições dos retratos pequenos | `config\profiles\pxg.json`, `team_slots` (os 5 primeiros) | (29,133) (24,177) (28,220) (31,269) (26,316) |
| Cor e área da barra de vida | `app\services\team_bar.py` (`HP_DX`, `HP_DY`, `HP_W`, `HP_H`, `HP_EMPTY`, `HP_ALIVE`) | verde (48,81,45) a (57,97,54) |
| Folga entre o Ctrl e o número | `app\services\action_executor.py`, `MODIFIER_LEAD_MS` | 40 ms |

## Pendências

- **A volta do 6 para o 1 não chama o Steelix.** O programa envia o `Ctrl+1` igual ao `Ctrl+2`; isso foi provado observando o teclado no Windows. À mão, o `Ctrl+1` funciona. **Teste pendente:** com o Pokémon 6 em campo, esperar uns 5 segundos e girar a roda. Se o Steelix sair, o jogo tem um tempo de espera, e a macro passa a respeitá-lo. Se não sair, apertar `Ctrl+1` à mão logo em seguida. Se assim funcionar, mudo o jeito de enviar essa tecla.
- **O revive pela barra de vida ainda não foi testado no jogo.** Se falhar, a linha do log que começa com "Barras de vida" mostra quanto verde o programa viu em cada retrato, e isso serve para calibrar.
- **Pokémon com pouca vida:** falta confirmar se ele pode ser confundido com um desmaiado. O Codex está testando isso na Rodada 5.

## Testes

- `python -B -m unittest test_rotation test_navigation test_game_profiles`: 23 testes passam.
- `python -B selfcheck.py`: 22 de 22 checagens passam.
- Os relatórios detalhados do Codex, rodadas 1 a 5, estão em [TESTE_TROCA_POKEMON.md](TESTE_TROCA_POKEMON.md).
