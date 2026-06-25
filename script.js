const boton = document.getElementById("saludo-btn");
const texto = document.getElementById("saludo-texto");

boton.addEventListener("click", () => {
  texto.textContent = "¡Hola! El JavaScript está funcionando correctamente.";
});
