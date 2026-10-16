# Mis Ubicaciones · web

Páginas públicas de la app Mis Ubicaciones, publicadas con GitHub Pages en
<https://jairosanchezb94.github.io/mis-ubicaciones/>:

- [Ayuda y contacto](https://jairosanchezb94.github.io/mis-ubicaciones/)
- [Política de privacidad](https://jairosanchezb94.github.io/mis-ubicaciones/privacidad/)
- [Condiciones de uso y aviso legal](https://jairosanchezb94.github.io/mis-ubicaciones/condiciones/)
- [Licencias de código abierto](https://jairosanchezb94.github.io/mis-ubicaciones/licencias/)

Solo HTML y CSS: sin scripts, fuentes externas, cookies ni analítica. El código de
la app está en otro repositorio, privado.

## Regenerar las licencias

`herramientas/licencias.py` rehace `licencias/index.html` con los paquetes que van
de verdad en la app: los de JavaScript salen del sourcemap del bundle de iOS y los
nativos, del archivo de reconocimientos de CocoaPods. Con un clon de la app en el
que ya se hayan ejecutado `npx expo prebuild --platform ios` y `pod install`:

```sh
npx expo export --platform ios --dump-sourcemap --output-dir /tmp/export-ios   # en el clon de la app
python3 -I herramientas/licencias.py <clon de la app> /tmp/export-ios licencias/index.html
```

`herramientas/licencias-extra/` guarda los textos de las bibliotecas que React
Native compila dentro de su propio framework (Folly, Boost, glog…).
