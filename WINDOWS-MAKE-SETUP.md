# Instalação do `make` no Windows com Winget e configuração do PATH

Para rodar comandos como:

```powershell
make docker-build
make docker-run
make docker-test
```

no PowerShell do Windows, é necessário instalar o **GNU Make** e garantir que o executável `make.exe` esteja disponível no `PATH` do sistema.

---

## 1. Instalar o Make com Winget

No PowerShell, execute:

```powershell
winget install GnuWin32.Make
```

Após a instalação, teste:

```powershell
make --version
```

Caso o PowerShell retorne o erro:

```txt
make : The term 'make' is not recognized
```

significa que o `make` foi instalado, mas o Windows ainda não sabe onde encontrar o executável.

---

## 2. Localizar o `make.exe`

Verifique se o executável existe no caminho padrão:

```powershell
& "C:\Program Files (x86)\GnuWin32\bin\make.exe" --version
```

Se esse comando retornar a versão do Make, a instalação está correta. O problema é apenas o `PATH`.

---

## 3. Adicionar o Make ao PATH

Adicione a pasta do `make.exe` ao `PATH` do usuário:

```powershell
setx PATH "$env:PATH;C:\Program Files (x86)\GnuWin32\bin"
```

Esse comando adiciona o seguinte diretório ao PATH:

```txt
C:\Program Files (x86)\GnuWin32\bin
```

---

## 4. Reiniciar o PowerShell

Depois de alterar o PATH, feche o PowerShell completamente e abra novamente.

Então teste:

```powershell
make --version
```

Se aparecer a versão do GNU Make, está tudo certo.

---

## 5. Rodar comandos do projeto

Agora, dentro da pasta do projeto que contém o `Makefile`, você pode rodar:

```powershell
make docker-build
```

ou:

```powershell
make docker-run
```

ou qualquer outro comando definido no `Makefile`.

---

## Resumo do problema

O Winget instalou o GNU Make corretamente, mas o executável ficou fora do `PATH`.

Por isso, o comando direto funcionava:

```powershell
& "C:\Program Files (x86)\GnuWin32\bin\make.exe" --version
```

mas o comando simples não:

```powershell
make --version
```

A correção foi adicionar a pasta `bin` do GnuWin32 ao `PATH` do Windows.
