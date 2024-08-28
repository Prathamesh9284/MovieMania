function showSeatings(movieId) {
  console.log(movieId);
  var url = 'seatbooking.php?value=' + movieId;
  window.location.href = url;
}

