(function() {
  var form, filmUrl, username;

  form = document.createElement('form');
  form.method = 'POST';
  form.action = '{{ url }}?nocache=' + Math.random();

  filmUrl = document.createElement('textarea');
  filmUrl.name = 'film_url';
  filmUrl.value = window.location.href;
  form.appendChild(filmUrl);

  username = document.createElement('textarea');
  username.name = 'username';
  username.value = '{{ username }}';
  form.appendChild(username);

  document.body.appendChild(form);

  form.submit();
})()
