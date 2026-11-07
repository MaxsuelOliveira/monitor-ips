# Padrão de README para projetos

[Exemplo em português](../README.md) · [Exemplo em inglês](../README.en.md)

Este padrão usa a composição do [README do Cap](https://github.com/CapSoftware/Cap#readme): logo, título e apresentação centralizados, links úteis, imagem do produto e seções objetivas. O Monitor IPS é a primeira aplicação deste padrão.

## Como aplicar

1. Copie apenas o bloco de modelo abaixo para o `README.md` na raiz do próximo projeto.
2. Substitua os campos `{{...}}` por informações verificadas. A frase inicial deve explicar o benefício e o público em uma linha.
3. Salve logo e screenshot em `documents/assets/`. Use o logo existente e uma captura real com dados de demonstração. Para APIs ou bibliotecas, substitua a imagem por um exemplo mínimo de requisição ou código.
4. Mantenha até cinco links no topo, com destinos existentes. Adicione download ou site somente quando estiverem disponíveis; sem links fictícios, badges estáticos de sucesso ou contagens inventadas.
5. Mostre um caminho principal para começar. Mova referência extensa, configuração e diagnóstico para guias em `documents/`; mantenha no README os requisitos e as limitações que afetam a decisão de usar o projeto.
6. Crie `README.en.md` com a mesma estrutura em inglês. Atualize os nomes das seções e todas as âncoras; no topo dele, aponte de volta para `README.md` com o rótulo Português.
7. Confira links relativos, imagens, títulos e tabelas em desktop e tela estreita. Não use os elementos de expansão nativa proibidos pelo projeto. Leia os comandos contra os scripts atuais, sem assumir que o ambiente do autor já está preparado.
8. Registre a licença realmente escolhida e as atribuições de terceiros. Quando a licença estiver pendente, informe isso explicitamente.

O padrão é de apresentação e conteúdo. Não exige trocar a stack, a marca ou a arquitetura de outros projetos. Preserve a pasta de documentação existente quando outro repositório já adotar uma convenção própria.

## Modelo para copiar

````markdown
<p align="center">
  <img width="150" height="150" src="documents/assets/logo.svg" alt="Logo de {{NOME}}">
</p>

<h1 align="center">{{NOME}}</h1>

<p align="center">
  {{UMA FRASE: O QUE RESOLVE E PARA QUEM}}
</p>

<p align="center">
  <a href="#começar">Começar</a>
  |
  <a href="#recursos">Recursos</a>
  |
  <a href="#documentação">Documentação</a>
  |
  <a href="#desenvolvimento">Desenvolvimento</a>
  |
  <a href="README.en.md">English</a>
</p>

<img src="documents/assets/preview.png" alt="{{DESCRIÇÃO ACESSÍVEL DA CAPTURA REAL}}">

{{PARÁGRAFO CURTO: O PRODUTO, O PROBLEMA E O CENÁRIO DE USO}}

{{PARÁGRAFO CURTO: COMO A PESSOA O UTILIZA}}

## Recursos

- **{{BENEFÍCIO}}.** {{COMPORTAMENTO REAL QUE O SUSTENTA}}
- **{{BENEFÍCIO}}.** {{COMPORTAMENTO REAL QUE O SUSTENTA}}
- **{{BENEFÍCIO}}.** {{COMPORTAMENTO REAL QUE O SUSTENTA}}

## Modos de uso

| Modo | Para quem | Como funciona |
| --- | --- | --- |
| {{MODO REAL}} | {{PÚBLICO}} | {{FLUXO}} |

## Começar

{{REQUISITOS, VERSÕES E PRÉ-CONDIÇÕES}}

```sh
{{COMANDOS VERIFICADOS DE INSTALAÇÃO E PRIMEIRO USO}}
```

{{PRIMEIRA AÇÃO QUE COMPROVA O FUNCIONAMENTO}}

## Documentação

{{LINKS RELATIVOS PARA GUIAS QUE EXISTEM}}

## Desenvolvimento

{{STACK E COMANDOS VERIFICADOS DE EXECUÇÃO, TESTE E BUILD}}

## Mapa do repositório

| Caminho | Responsabilidade |
| --- | --- |
| {{PASTA REAL}} | {{RESPONSABILIDADE}} |

## Limitações

{{LIMITES CONHECIDOS E COMPATIBILIDADE COMPROVADA}}

## Contribuição

{{COMO RELATAR UM PROBLEMA E VALIDAR UMA CONTRIBUIÇÃO}}

## Licenciamento

{{LICENÇA ESCOLHIDA E LINK DO ARQUIVO, OU SITUAÇÃO PENDENTE}}

{{ATRIBUIÇÕES NECESSÁRIAS}}
````

## Antes de publicar

- O primeiro bloco explica o produto sem depender de um screenshot.
- A captura mostra o estado atual, com texto legível e sem dados privados.
- Todos os campos do modelo foram substituídos ou a seção foi removida quando não se aplica.
- O leitor consegue reproduzir o início rápido em uma máquina preparada com os requisitos documentados.
- As duas versões do README descrevem as mesmas capacidades e limitações.
- Links, âncoras, licenciamento e informações de contribuição correspondem ao repositório de destino.
