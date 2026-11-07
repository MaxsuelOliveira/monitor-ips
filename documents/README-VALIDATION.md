# Validação da documentação — 07/11/2026

## Referência e alterações

- Composição do [README do Cap](https://github.com/CapSoftware/Cap#readme): logo de 150 × 150 px, título e descrição centralizados, navegação e screenshot amplo.
- Cópia original em `output/reference/Cap-README.md`; URL, data e SHA-256 em `output/reference/source.json`. Essa referência local é ignorada pelo Git.
- README principal em português e versão equivalente em inglês. O screenshot retrata a interface em português e os guias detalhados continuam nesse idioma, conforme informado na versão inglesa.
- Conteúdo técnico do README anterior preservado nos guias de uso e desenvolvimento. Exemplos ativos generalizados, sem caminhos absolutos ou IDs de monitores da máquina do autor.
- Modelo reutilizável e instruções em [README-TEMPLATE.md](README-TEMPLATE.md).

## Captura e apresentação

- Screenshot real do Electron em `--demo --qa`, viewport de 1440 × 1024, sem aplicar ajustes ao hardware real. Asset em [assets/monitor-ips-demo.png](assets/monitor-ips-demo.png).
- Logo exportado da marca existente no aplicativo; origem em [assets/SOURCES.md](assets/SOURCES.md).
- Prévia local das duas versões renderizada como GitHub Flavored Markdown com Marked 17.0.1 e estilos de `sindresorhus/github-markdown-css`. Não representa uma publicação ou verificação no GitHub hospedado.
- Desktop 1440 × 1080 e viewport estreito 390 × 844: logo, screenshot, títulos, tabelas e navegação examinados. Imagens carregadas e scrollWidth igual a 390 no viewport de 390 px em ambos os idiomas.
- Testados o link Começar e a troca PT-BR → inglês → PT-BR. Nenhum erro de página registrado pelo Agent Browser.
- Capturas e metadados temporários em `output/readme-preview/`, ignorado pelo Git.

## Verificações

- Checagem final de links, imagens e âncoras nos sete documentos novos ou reestruturados: 57 destinos locais aprovados.
- Ausência das tags de expansão nativa proibidas nos documentos ativos. Campos de modelo aparecem somente no bloco de código que deve ser copiado e preenchido.
- Requisitos de Node comparados com `package-lock.json`; comandos npm comparados com `package.json`. Entradas Python e launchers comparados com os arquivos presentes.
- `python monitor_ips.py --help` e `python monitor_ips.py --demo list --json`: aprovados.
- Prévia `--demo preset --monitor demo-va --panel va --name oled-balanced --dry-run`: aprovada.
- `python -m unittest discover -s tests -v`: 71 testes aprovados.
- `python -m compileall -q monitor_ips.py monitor_tool tests scripts`: aprovado.
- `npm test`: integração Electron/Python aprovada.
- `npm run check`: aprovado.
- `git diff --check`: aprovado.
- Recursos temporários encerrados: Electron QA e processo Python filho, sessão de navegador da captura, sessão da prévia e servidor local. Confirmada a ausência do processo de preview e de listener em sua porta após o encerramento.

## Limites

Não foi executada uma instalação do zero em outro Windows. As dependências já estavam presentes no ambiente de validação. Não houve publicação, configuração de remoto nem escolha de licença para o código próprio. Relatórios históricos de testes continuam registrando seus ambientes originais; esta tarefa generalizou os exemplos dos novos guias públicos.
