n = 1;
// X es desde donde quiero comenzar a eliminar
// N Es donde quiero terminar
$('#miTabla tr').each(function() {
   if (n > X && n < N)
      $(this).remove();
   n++;
});
