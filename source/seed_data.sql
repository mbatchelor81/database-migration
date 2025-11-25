-- Seed data for Project Management Application
-- Creates realistic sample data for demo purposes

-- Insert Organizations
INSERT INTO organizations (name, created_at) VALUES
('Acme Corporation', '2024-01-15 10:00:00+00'),
('TechStart Inc', '2024-02-20 14:30:00+00'),
('Global Solutions Ltd', '2024-03-10 09:15:00+00');

-- Insert Users
INSERT INTO users (email, name, created_at) VALUES
('alice@acme.com', 'Alice Johnson', '2024-01-16 08:00:00+00'),
('bob@acme.com', 'Bob Smith', '2024-01-17 09:30:00+00'),
('carol@acme.com', 'Carol Williams', '2024-01-18 11:00:00+00'),
('david@techstart.com', 'David Brown', '2024-02-21 10:00:00+00'),
('emma@techstart.com', 'Emma Davis', '2024-02-22 13:45:00+00'),
('frank@techstart.com', 'Frank Miller', '2024-02-23 15:20:00+00'),
('grace@global.com', 'Grace Wilson', '2024-03-11 08:30:00+00'),
('henry@global.com', 'Henry Moore', '2024-03-12 10:15:00+00'),
('iris@global.com', 'Iris Taylor', '2024-03-13 14:00:00+00'),
('jack@acme.com', 'Jack Anderson', '2024-01-20 09:00:00+00'),
('kate@techstart.com', 'Kate Thomas', '2024-02-25 11:30:00+00'),
('leo@global.com', 'Leo Jackson', '2024-03-14 16:45:00+00');

-- Insert Organization Members
-- Acme Corporation members
INSERT INTO org_members (org_id, user_id, role, joined_at) VALUES
(1, 1, 'admin', '2024-01-16 08:00:00+00'),
(1, 2, 'member', '2024-01-17 09:30:00+00'),
(1, 3, 'member', '2024-01-18 11:00:00+00'),
(1, 10, 'member', '2024-01-20 09:00:00+00');

-- TechStart Inc members
INSERT INTO org_members (org_id, user_id, role, joined_at) VALUES
(2, 4, 'admin', '2024-02-21 10:00:00+00'),
(2, 5, 'member', '2024-02-22 13:45:00+00'),
(2, 6, 'member', '2024-02-23 15:20:00+00'),
(2, 11, 'member', '2024-02-25 11:30:00+00');

-- Global Solutions Ltd members
INSERT INTO org_members (org_id, user_id, role, joined_at) VALUES
(3, 7, 'admin', '2024-03-11 08:30:00+00'),
(3, 8, 'member', '2024-03-12 10:15:00+00'),
(3, 9, 'member', '2024-03-13 14:00:00+00'),
(3, 12, 'member', '2024-03-14 16:45:00+00');

-- Some users belong to multiple organizations
INSERT INTO org_members (org_id, user_id, role, joined_at) VALUES
(2, 1, 'member', '2024-03-01 10:00:00+00'),
(3, 4, 'member', '2024-03-15 14:00:00+00');

-- Insert Projects
INSERT INTO projects (org_id, name, description, status, created_at) VALUES
(1, 'Website Redesign', 'Complete overhaul of company website', 'active', '2024-01-20 10:00:00+00'),
(1, 'Mobile App Development', 'Native mobile app for iOS and Android', 'active', '2024-02-01 09:00:00+00'),
(1, 'Customer Portal', 'Self-service portal for customers', 'planning', '2024-03-05 14:00:00+00'),
(2, 'Product Launch Q2', 'Launch new product line in Q2', 'active', '2024-02-25 11:00:00+00'),
(2, 'Marketing Campaign', 'Digital marketing campaign for brand awareness', 'active', '2024-03-01 10:30:00+00'),
(2, 'Infrastructure Upgrade', 'Migrate to cloud infrastructure', 'completed', '2024-01-10 08:00:00+00'),
(3, 'ERP Implementation', 'Implement new ERP system', 'active', '2024-03-15 09:00:00+00'),
(3, 'Security Audit', 'Comprehensive security audit and remediation', 'active', '2024-03-20 13:00:00+00');

-- Insert Labels
INSERT INTO labels (org_id, name, color) VALUES
(1, 'Bug', '#FF0000'),
(1, 'Feature', '#00FF00'),
(1, 'Enhancement', '#0000FF'),
(1, 'Urgent', '#FF6600'),
(2, 'Bug', '#FF0000'),
(2, 'Feature', '#00FF00'),
(2, 'Documentation', '#FFFF00'),
(2, 'Testing', '#FF00FF'),
(3, 'Bug', '#FF0000'),
(3, 'Feature', '#00FF00'),
(3, 'Security', '#800080'),
(3, 'Performance', '#FFA500');

-- Insert Tasks for Project 1 (Website Redesign)
INSERT INTO tasks (project_id, title, description, status, priority, due_date, created_at) VALUES
(1, 'Design homepage mockup', 'Create initial design mockups for the new homepage', 'completed', 'high', '2024-01-25 17:00:00+00', '2024-01-20 10:30:00+00'),
(1, 'Implement responsive navigation', 'Build mobile-responsive navigation menu', 'in_progress', 'high', '2024-04-10 17:00:00+00', '2024-01-22 09:00:00+00'),
(1, 'Set up content management system', 'Configure CMS for easy content updates', 'todo', 'medium', '2024-04-15 17:00:00+00', '2024-01-23 14:00:00+00'),
(1, 'Optimize images for web', 'Compress and optimize all website images', 'in_progress', 'low', '2024-04-12 17:00:00+00', '2024-01-24 11:00:00+00');

-- Insert Tasks for Project 2 (Mobile App Development)
INSERT INTO tasks (project_id, title, description, status, priority, due_date, created_at) VALUES
(2, 'Set up development environment', 'Configure React Native development environment', 'completed', 'high', '2024-02-05 17:00:00+00', '2024-02-01 09:30:00+00'),
(2, 'Design app architecture', 'Plan app structure and component hierarchy', 'completed', 'high', '2024-02-08 17:00:00+00', '2024-02-02 10:00:00+00'),
(2, 'Implement user authentication', 'Add login and registration functionality', 'in_progress', 'high', '2024-04-20 17:00:00+00', '2024-02-05 13:00:00+00'),
(2, 'Create dashboard screen', 'Build main dashboard with key metrics', 'todo', 'medium', '2024-04-25 17:00:00+00', '2024-02-06 15:00:00+00'),
(2, 'Add push notifications', 'Implement push notification system', 'todo', 'medium', '2024-05-01 17:00:00+00', '2024-02-07 11:00:00+00');

-- Insert Tasks for Project 4 (Product Launch Q2)
INSERT INTO tasks (project_id, title, description, status, priority, due_date, created_at) VALUES
(4, 'Finalize product specifications', 'Complete detailed product specifications document', 'completed', 'high', '2024-03-01 17:00:00+00', '2024-02-25 11:30:00+00'),
(4, 'Create marketing materials', 'Design brochures, presentations, and website content', 'in_progress', 'high', '2024-04-15 17:00:00+00', '2024-02-26 14:00:00+00'),
(4, 'Set up distribution channels', 'Establish partnerships with distributors', 'in_progress', 'high', '2024-04-20 17:00:00+00', '2024-02-27 10:00:00+00'),
(4, 'Plan launch event', 'Organize product launch event and invitations', 'todo', 'medium', '2024-05-15 17:00:00+00', '2024-02-28 16:00:00+00');

-- Insert Tasks for Project 5 (Marketing Campaign)
INSERT INTO tasks (project_id, title, description, status, priority, due_date, created_at) VALUES
(5, 'Define target audience', 'Research and define target customer segments', 'completed', 'high', '2024-03-05 17:00:00+00', '2024-03-01 11:00:00+00'),
(5, 'Create social media content', 'Develop content calendar for social media', 'in_progress', 'high', '2024-04-10 17:00:00+00', '2024-03-02 13:00:00+00'),
(5, 'Design banner ads', 'Create display ads for online advertising', 'in_progress', 'medium', '2024-04-12 17:00:00+00', '2024-03-03 15:00:00+00'),
(5, 'Set up email campaign', 'Configure email marketing automation', 'todo', 'medium', '2024-04-18 17:00:00+00', '2024-03-04 09:00:00+00'),
(5, 'Track campaign metrics', 'Set up analytics and tracking dashboards', 'todo', 'low', '2024-04-20 17:00:00+00', '2024-03-04 14:00:00+00');

-- Insert Tasks for Project 7 (ERP Implementation)
INSERT INTO tasks (project_id, title, description, status, priority, due_date, created_at) VALUES
(7, 'Assess current systems', 'Audit existing business processes and systems', 'completed', 'high', '2024-03-20 17:00:00+00', '2024-03-15 09:30:00+00'),
(7, 'Select ERP vendor', 'Evaluate and choose ERP solution provider', 'in_progress', 'high', '2024-04-05 17:00:00+00', '2024-03-16 10:00:00+00'),
(7, 'Plan data migration', 'Design strategy for migrating existing data', 'todo', 'high', '2024-04-15 17:00:00+00', '2024-03-17 14:00:00+00'),
(7, 'Train staff', 'Conduct training sessions for all users', 'todo', 'medium', '2024-05-01 17:00:00+00', '2024-03-18 11:00:00+00');

-- Insert Tasks for Project 8 (Security Audit)
INSERT INTO tasks (project_id, title, description, status, priority, due_date, created_at) VALUES
(8, 'Conduct vulnerability scan', 'Run automated security scanning tools', 'in_progress', 'high', '2024-04-01 17:00:00+00', '2024-03-20 13:30:00+00'),
(8, 'Review access controls', 'Audit user permissions and access levels', 'in_progress', 'high', '2024-04-05 17:00:00+00', '2024-03-21 10:00:00+00'),
(8, 'Update security policies', 'Revise company security policies and procedures', 'todo', 'medium', '2024-04-10 17:00:00+00', '2024-03-22 15:00:00+00'),
(8, 'Implement two-factor authentication', 'Roll out 2FA for all user accounts', 'todo', 'high', '2024-04-15 17:00:00+00', '2024-03-23 09:00:00+00');

-- Insert Task Assignees
INSERT INTO task_assignees (task_id, user_id, assigned_at) VALUES
-- Website Redesign tasks
(1, 1, '2024-01-20 10:30:00+00'),
(1, 3, '2024-01-20 11:00:00+00'),
(2, 2, '2024-01-22 09:00:00+00'),
(2, 10, '2024-01-22 09:30:00+00'),
(3, 1, '2024-01-23 14:00:00+00'),
(4, 3, '2024-01-24 11:00:00+00'),
-- Mobile App tasks
(5, 2, '2024-02-01 09:30:00+00'),
(6, 2, '2024-02-02 10:00:00+00'),
(6, 10, '2024-02-02 10:30:00+00'),
(7, 1, '2024-02-05 13:00:00+00'),
(7, 2, '2024-02-05 13:30:00+00'),
(8, 10, '2024-02-06 15:00:00+00'),
(9, 3, '2024-02-07 11:00:00+00'),
-- Product Launch tasks
(10, 4, '2024-02-25 11:30:00+00'),
(11, 5, '2024-02-26 14:00:00+00'),
(11, 11, '2024-02-26 14:30:00+00'),
(12, 6, '2024-02-27 10:00:00+00'),
(13, 4, '2024-02-28 16:00:00+00'),
(13, 5, '2024-02-28 16:30:00+00'),
-- Marketing Campaign tasks
(14, 5, '2024-03-01 11:00:00+00'),
(15, 11, '2024-03-02 13:00:00+00'),
(16, 5, '2024-03-03 15:00:00+00'),
(17, 6, '2024-03-04 09:00:00+00'),
(18, 11, '2024-03-04 14:00:00+00'),
-- ERP Implementation tasks
(19, 7, '2024-03-15 09:30:00+00'),
(19, 8, '2024-03-15 10:00:00+00'),
(20, 7, '2024-03-16 10:00:00+00'),
(21, 9, '2024-03-17 14:00:00+00'),
(22, 12, '2024-03-18 11:00:00+00'),
-- Security Audit tasks
(23, 8, '2024-03-20 13:30:00+00'),
(23, 12, '2024-03-20 14:00:00+00'),
(24, 7, '2024-03-21 10:00:00+00'),
(25, 9, '2024-03-22 15:00:00+00'),
(26, 8, '2024-03-23 09:00:00+00');

-- Insert Task Labels
INSERT INTO task_labels (task_id, label_id) VALUES
-- Website Redesign
(1, 2), (1, 3),
(2, 2), (2, 4),
(3, 2),
(4, 3),
-- Mobile App
(5, 2),
(6, 2),
(7, 2), (7, 4),
(8, 2),
(9, 2),
-- Product Launch
(10, 6), (10, 8),
(11, 6),
(12, 6),
(13, 6),
-- Marketing Campaign
(14, 7),
(15, 6), (15, 7),
(16, 6),
(17, 6),
(18, 8),
-- ERP Implementation
(19, 10),
(20, 10),
(21, 10),
(22, 10),
-- Security Audit
(23, 11), (23, 12),
(24, 11),
(25, 11),
(26, 11), (26, 12);

-- Insert Comments
INSERT INTO comments (task_id, user_id, content, created_at) VALUES
-- Comments on Website Redesign tasks
(1, 1, 'Initial mockups look great! Let''s proceed with this direction.', '2024-01-21 09:00:00+00'),
(1, 3, 'Agreed, the color scheme is perfect for our brand.', '2024-01-21 10:30:00+00'),
(2, 2, 'Working on the mobile breakpoints now.', '2024-01-23 14:00:00+00'),
(2, 10, 'I can help with the hamburger menu animation.', '2024-01-23 15:30:00+00'),
(2, 1, 'Great! Let''s sync up tomorrow to review progress.', '2024-01-23 16:00:00+00'),
(3, 1, 'Evaluating WordPress vs. custom CMS options.', '2024-01-24 10:00:00+00'),
(4, 3, 'Using WebP format for better compression.', '2024-01-25 11:00:00+00'),
-- Comments on Mobile App tasks
(5, 2, 'Environment setup complete. Ready to start development.', '2024-02-02 08:00:00+00'),
(6, 10, 'Created initial component structure diagram.', '2024-02-03 13:00:00+00'),
(7, 1, 'Implementing OAuth 2.0 for authentication.', '2024-02-06 09:00:00+00'),
(7, 2, 'Should we support biometric login as well?', '2024-02-06 10:30:00+00'),
(7, 1, 'Yes, let''s add that to the scope.', '2024-02-06 11:00:00+00'),
(8, 10, 'Wireframes for dashboard are ready for review.', '2024-02-07 14:00:00+00'),
-- Comments on Product Launch tasks
(10, 4, 'Specifications document finalized and approved.', '2024-03-02 09:00:00+00'),
(11, 5, 'First draft of marketing materials ready.', '2024-03-05 10:00:00+00'),
(11, 11, 'The product photos look amazing!', '2024-03-05 11:30:00+00'),
(12, 6, 'Met with three potential distributors this week.', '2024-03-08 15:00:00+00'),
(13, 4, 'Venue booked for May 15th launch event.', '2024-03-10 13:00:00+00'),
-- Comments on Marketing Campaign tasks
(14, 5, 'Target audience research complete. Focusing on 25-40 age group.', '2024-03-06 09:00:00+00'),
(15, 11, 'Content calendar created for next 3 months.', '2024-03-07 14:00:00+00'),
(15, 5, 'Looks good! Let''s schedule the posts.', '2024-03-07 15:30:00+00'),
(16, 5, 'Banner ads designed in 5 different sizes.', '2024-03-08 11:00:00+00'),
-- Comments on ERP Implementation tasks
(19, 7, 'Current systems assessment report is ready.', '2024-03-21 10:00:00+00'),
(19, 8, 'Identified several process improvement opportunities.', '2024-03-21 11:30:00+00'),
(20, 7, 'Narrowed down to two vendors. Scheduling demos.', '2024-03-22 13:00:00+00'),
(21, 9, 'Data migration will be the most complex part.', '2024-03-23 09:00:00+00'),
-- Comments on Security Audit tasks
(23, 8, 'Vulnerability scan revealed 3 critical issues.', '2024-03-21 15:00:00+00'),
(23, 12, 'Working on patches for the critical vulnerabilities.', '2024-03-22 09:00:00+00'),
(24, 7, 'Found several users with excessive permissions.', '2024-03-22 14:00:00+00'),
(25, 9, 'Drafting updated security policy document.', '2024-03-23 10:00:00+00'),
(26, 8, '2FA implementation plan created. Starting rollout next week.', '2024-03-24 11:00:00+00');
