# Bisbo

Bot de Discord desenvolvido em Python para uso em um único servidor. O
projeto reúne comandos de interação e está sendo expandido com sistemas
persistentes de perfil, experiência, economia e profissões.

## Comandos

  -----------------------------------------------------------------------
  Comando                             Função
  ----------------------------------- -----------------------------------
  `/perfil`                           Exibe o perfil do próprio usuário
                                      ou de outro membro do servidor.

  `/ping`                             Verifica a resposta do bot.

  `/bighead`                          Comando de interação com imagens no
                                      estilo Bighead.

  `/bispo`                            Pesquisa imagens a partir de uma
                                      consulta.
  -----------------------------------------------------------------------

### `/perfil`

O comando exibe um perfil individual. Também permite consultar o perfil
de outro membro.

**Usos:** - `/perfil` - `/perfil membro:@usuário`

O perfil apresenta as seções de identidade, experiência, economia e
profissão. O nome e o avatar são obtidos do Discord; os dados
persistentes do perfil ficam no PostgreSQL.

Se o membro ainda não tiver um registro, o comando cria seu perfil com
os valores iniciais abaixo.

  Campo                  Valor inicial
  -------------------- ---------------
  Nível                              1
  XP no nível                        0
  Carteira                           0
  Banco                              0
  Profissão                    Nenhuma
  Nível profissional                 0

O patrimônio é calculado pela soma da carteira e do banco. O comando
`/perfil` exibe os dados; ele não concede XP, altera saldos nem gerencia
profissões.

### `/ping`

Comando para verificar a resposta do Bisbo.

### `/bighead`

Comando de interação com imagens no estilo Bighead.

### `/bispo`

Comando de pesquisa de imagens. A pesquisa é realizada a partir de uma
consulta fornecida no comando.

> Os parâmetros e as opções de `/ping`, `/bighead` e `/bispo` devem ser
> conferidos na interface de comandos do Discord, pois podem mudar
> conforme a implementação.

## Sistemas

### Perfil --- implementado

O sistema de perfil mantém um registro por usuário do servidor. Os dados
são persistidos no PostgreSQL e consultados pelo comando `/perfil`.

### XP e níveis --- planejado

O sistema de XP ainda será desenvolvido. A primeira forma prevista de
obtenção de experiência será por mensagens válidas no chat. No futuro,
outras fontes de XP poderão ser adicionadas.

As regras já definidas para a progressão são:

-   A cada 5 mensagens válidas, o usuário recebe 10 XP.
-   O XP necessário para avançar é calculado por `20 × nível atual`.
-   O XP é armazenado dentro do nível atual.
-   Ao subir de nível, o excedente de XP é preservado.

Até a implementação do sistema, esses valores representam o planejamento
e não uma funcionalidade ativa do bot.

### Economia --- planejado

O sistema de economia deverá gerenciar carteira, banco e transações. O
perfil já possui campos para exibir carteira, banco e patrimônio, mas o
sistema de movimentação de dinheiro ainda será desenvolvido.

### Empregos e profissões --- planejado

O sistema de empregos deverá gerenciar a profissão do usuário e sua
progressão profissional. O perfil já reserva campos para profissão e
nível profissional; as regras de trabalho ainda serão implementadas.
