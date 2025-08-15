// Function to show a toast notification
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    
    // Remove toast after animation
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

// Function to handle form submission and log in
async function handleLogin(event) {
    event.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    const loginData = { email: email, password: password };
    const backendUrl = 'http://127.0.0.1:5000/api/login';

    try {
        const response = await fetch(backendUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(loginData)
        });

        const data = await response.json();

        if (response.ok) {
            localStorage.setItem('accessToken', data.access_token);
            localStorage.setItem('userRole', data.user.role);
            localStorage.setItem('userId', data.user.id);
            localStorage.setItem('userName', data.user.first_name);

            showToast('Login successful!', 'success');
            console.log('Access Token:', data.access_token);
            console.log('User Role:', data.user.role);

            document.getElementById('logout-button').style.display = 'block';
            renderDashboard(data.user.role);
        } else {
            showToast(data.message, 'error');
        }
    } catch (error) {
        showToast('Network error. Is the Flask server running?', 'error');
        console.error('Network error:', error);
    }
}

// Function to handle the creation of a new post
async function handleCreatePost(event) {
    event.preventDefault();
    const title = document.getElementById('post-title').value;
    const content = document.getElementById('post-content').value;
    const classId = 1;
    
    const postData = { title, content, class_id: classId };
    
    const backendUrl = 'http://127.0.0.1:5000/api/teacher/create_post';
    const accessToken = localStorage.getItem('accessToken');

    try {
        const response = await fetch(backendUrl, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify(postData)
        });

        const data = await response.json();

        if (response.ok) {
            showToast('Post created successfully!', 'success');
            document.getElementById('post-form').reset();
        } else {
            showToast(data.message, 'error');
        }
    } catch (error) {
        showToast('Network error.', 'error');
        console.error('Network error:', error);
    }
}

// Function to handle post deletion for admins
async function handleDeletePost(postId) {
    const backendUrl = `http://127.0.0.1:5000/api/admin/delete_post/${postId}`;
    const accessToken = localStorage.getItem('accessToken');

    try {
        const response = await fetch(backendUrl, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });
        
        if (response.ok) {
            showToast(`Post deleted successfully.`, 'success');
            fetchPosts('school_admin'); 
        } else {
            const data = await response.json();
            showToast(`Failed to delete post: ${data.message}`, 'error');
        }
    } catch (error) {
        showToast('Network error during deletion.', 'error');
        console.error('Network error:', error);
    }
}

// Helper function to format the timestamp
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return date.toLocaleDateString('en-US', options);
}

// Function to fetch and display posts for different roles
async function fetchPosts(role) {
    let endpoint;
    let listElementId;
    
    if (role === 'school_admin') {
        endpoint = 'http://127.0.0.1:5000/api/admin/posts';
        listElementId = 'admin-posts-list';
    } else if (role === 'parent') {
        endpoint = 'http://127.0.0.1:5000/api/parent/posts';
        listElementId = 'parent-posts-list';
    } else {
        endpoint = 'http://127.0.0.1:5000/api/student/posts';
        listElementId = 'posts-list';
    }

    const accessToken = localStorage.getItem('accessToken');
    const postsList = document.getElementById(listElementId);
    
    if (!postsList) return;
    
    postsList.innerHTML = '<p class="loading">Loading posts...</p>';

    try {
        const response = await fetch(endpoint, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });
        
        const posts = await response.json();

        if (response.ok) {
            postsList.innerHTML = '';
            if (posts.length === 0) {
                postsList.innerHTML = '<p class="info">No posts to display.</p>';
            } else {
                posts.forEach(post => {
                    const postCard = document.createElement('div');
                    postCard.className = 'card';
                    
                    let cardContent = `
                        <h4>${post.title}</h4>
                        <p>${post.content}</p>
                        <small>Posted by ${post.author_first_name} ${post.author_last_name} in ${post.class_name} on ${formatTimestamp(post.created_at)}</small>
                    `;
                    
                    if (role === 'school_admin') {
                        cardContent += `<button class="delete-btn" onclick="handleDeletePost(${post.id})">Delete</button>`;
                    }
                    
                    postCard.innerHTML = cardContent;
                    postsList.appendChild(postCard);
                });
            }
        } else {
            postsList.innerHTML = `<p class="error-message">Error fetching posts: ${posts.message}</p>`;
        }
    } catch (error) {
        postsList.innerHTML = '<p class="error-message">Network error fetching posts.</p>';
        console.error('Network error:', error);
    }
}

// Master function to render the correct dashboard
function renderDashboard(role) {
    document.querySelectorAll('.section').forEach(section => {
        section.style.display = 'none';
    });
    document.getElementById('login-section').style.display = 'none';
    document.getElementById('dashboard-header').style.display = 'flex';

    const userName = localStorage.getItem('userName');
    const roleText = role.replace('_', ' ');
    document.getElementById('welcome-message').textContent = `Welcome, ${userName}! (${roleText})`;

    const sectionId = `${role.replace('school_', '')}-dashboard-section`;
    const dashboardSection = document.getElementById(sectionId);
    if (dashboardSection) {
        dashboardSection.style.display = 'block';
        if (role === 'student' || role === 'parent' || role === 'school_admin') {
            fetchPosts(role);
        }
    }
}

// Function to handle logout
function handleLogout() {
    localStorage.clear();
    location.reload();
}

// Theme Toggle Logic
function toggleTheme() {
    const isDarkMode = document.body.classList.toggle('dark-mode');
    localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
    document.getElementById('theme-toggle').textContent = isDarkMode ? 'Light Mode' : 'Dark Mode';
}

function loadTheme() {
    const savedTheme = localStorage.getItem('theme');
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        if (themeToggleBtn) {
            themeToggleBtn.textContent = 'Light Mode';
        }
    } else {
        document.body.classList.remove('dark-mode');
        if (themeToggleBtn) {
            themeToggleBtn.textContent = 'Dark Mode';
        }
    }
}

// Check for existing token and theme preference on page load
document.addEventListener('DOMContentLoaded', () => {
    loadTheme();
    
    const accessToken = localStorage.getItem('accessToken');
    const userRole = localStorage.getItem('userRole');

    if (accessToken && userRole) {
        document.getElementById('logout-button').style.display = 'block';
        renderDashboard(userRole);
    } else {
        document.getElementById('login-section').style.display = 'block';
    }

    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    const postForm = document.getElementById('post-form');
    if (postForm) {
        postForm.addEventListener('submit', handleCreatePost);
    }
    
    const logoutButton = document.getElementById('logout-button');
    if (logoutButton) {
        logoutButton.addEventListener('click', handleLogout);
    }
    
    const themeToggleButton = document.getElementById('theme-toggle');
    if (themeToggleButton) {
        themeToggleButton.addEventListener('click', toggleTheme);
    }
});