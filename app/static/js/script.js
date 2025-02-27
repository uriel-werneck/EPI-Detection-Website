document.addEventListener('DOMContentLoaded', function() {
    const header = document.getElementById('header');
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            header.classList.add('bg-white', 'shadow');
            header.classList.remove('bg-transparent');
        } else {
            header.classList.remove('bg-white', 'shadow');
            header.classList.add('bg-transparent');
        }
    });
});