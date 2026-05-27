# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, AccessError


class TestSuTaskStateMachine(TransactionCase):
    """Test state transitions and guard conditions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['su.project'].create({
            'name': 'Тестовый объект',
        })
        cls.brigade = cls.env['su.brigade'].create({
            'name': 'Бригада 1',
        })

    def _create_task(self, **kwargs):
        vals = {
            'name': 'Тестовая задача',
            'project_id': self.project.id,
        }
        vals.update(kwargs)
        return self.env['su.task'].create(vals)

    def test_state_new_to_in_progress(self):
        """Happy path: new task can start."""
        task = self._create_task()
        self.assertEqual(task.state, 'new')
        task.action_start()
        self.assertEqual(task.state, 'in_progress')

    def test_state_in_progress_to_review(self):
        """Task in progress can be sent for review."""
        task = self._create_task(state='in_progress')
        task.action_review()
        self.assertEqual(task.state, 'review')

    def test_state_review_to_done(self):
        """Task on review can be completed."""
        task = self._create_task(state='review')
        task.action_done()
        self.assertEqual(task.state, 'done')
        self.assertEqual(task.progress, 100.0)

    def test_action_done_sets_progress_100(self):
        """action_done forces progress to 100%."""
        task = self._create_task(state='review')
        task.action_done()
        self.assertEqual(task.progress_manual, 100.0)
        self.assertEqual(task.progress, 100.0)

    def test_reopen_from_review(self):
        """Task on review can be reopened."""
        task = self._create_task(state='review')
        task.action_reopen()
        self.assertEqual(task.state, 'in_progress')

    def test_reopen_from_done_resets_progress(self):
        """Reopening a done task sets progress to 99%."""
        task = self._create_task(state='done')
        task.progress_manual = 100.0
        task.action_reopen()
        self.assertEqual(task.state, 'in_progress')
        self.assertEqual(task.progress_manual, 99.0)

    def test_cancel_from_new(self):
        """New task can be cancelled."""
        task = self._create_task()
        task.action_cancel()
        self.assertEqual(task.state, 'cancelled')

    def test_cancel_done_raises(self):
        """Cannot cancel a done task."""
        task = self._create_task(state='done')
        with self.assertRaises(ValidationError):
            task.action_cancel()

    def test_cancel_cancelled_raises(self):
        """Cannot cancel an already cancelled task."""
        task = self._create_task(state='cancelled')
        with self.assertRaises(ValidationError):
            task.action_cancel()

    def test_start_not_new_raises(self):
        """Cannot start a task that is not new."""
        task = self._create_task(state='in_progress')
        with self.assertRaises(ValidationError):
            task.action_start()

    def test_review_not_in_progress_raises(self):
        """Cannot send to review a task not in progress."""
        task = self._create_task(state='new')
        with self.assertRaises(ValidationError):
            task.action_review()

    def test_done_not_review_raises(self):
        """Cannot complete a task not on review."""
        task = self._create_task(state='in_progress')
        with self.assertRaises(ValidationError):
            task.action_done()


class TestSuTaskBlocked(TransactionCase):
    """Test dependency engine and blocked detection."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['su.project'].create({
            'name': 'Тестовый объект',
        })

    def test_blocked_by_incomplete_dependency(self):
        """Task with incomplete dependency is blocked."""
        dep = self.env['su.task'].create({
            'name': 'Зависимость',
            'project_id': self.project.id,
            'state': 'new',
        })
        task = self.env['su.task'].create({
            'name': 'Задача',
            'project_id': self.project.id,
            'dependency_ids': [(4, dep.id)],
        })
        self.assertTrue(task.is_blocked)

    def test_unblocked_when_dependency_done(self):
        """Task unblocked when dependency is done."""
        dep = self.env['su.task'].create({
            'name': 'Зависимость',
            'project_id': self.project.id,
            'state': 'new',
        })
        task = self.env['su.task'].create({
            'name': 'Задача',
            'project_id': self.project.id,
            'dependency_ids': [(4, dep.id)],
        })
        self.assertTrue(task.is_blocked)
        dep.state = 'in_progress'
        dep.state = 'review'
        dep.state = 'done'
        self.assertFalse(task.is_blocked)

    def test_unblocked_when_dependency_cancelled(self):
        """Task unblocked when dependency is cancelled."""
        dep = self.env['su.task'].create({
            'name': 'Зависимость',
            'project_id': self.project.id,
            'state': 'new',
        })
        task = self.env['su.task'].create({
            'name': 'Задача',
            'project_id': self.project.id,
            'dependency_ids': [(4, dep.id)],
        })
        dep.state = 'cancelled'
        self.assertFalse(task.is_blocked)

    def test_blocked_cannot_start(self):
        """Blocked task raises on action_start."""
        dep = self.env['su.task'].create({
            'name': 'Зависимость',
            'project_id': self.project.id,
            'state': 'in_progress',
        })
        task = self.env['su.task'].create({
            'name': 'Задача',
            'project_id': self.project.id,
            'dependency_ids': [(4, dep.id)],
        })
        with self.assertRaises(ValidationError):
            task.action_start()

    def test_circular_dependency_raises(self):
        """Direct circular dependency A→B→A raises."""
        task_a = self.env['su.task'].create({
            'name': 'A',
            'project_id': self.project.id,
        })
        task_b = self.env['su.task'].create({
            'name': 'B',
            'project_id': self.project.id,
            'dependency_ids': [(4, task_a.id)],
        })
        with self.assertRaises(ValidationError):
            task_a.write({'dependency_ids': [(4, task_b.id)]})

    def test_deep_circular_dependency_raises(self):
        """Deep circular A→B→C→A raises."""
        task_a = self.env['su.task'].create({
            'name': 'A',
            'project_id': self.project.id,
        })
        task_b = self.env['su.task'].create({
            'name': 'B',
            'project_id': self.project.id,
            'dependency_ids': [(4, task_a.id)],
        })
        task_c = self.env['su.task'].create({
            'name': 'C',
            'project_id': self.project.id,
            'dependency_ids': [(4, task_b.id)],
        })
        with self.assertRaises(ValidationError):
            task_a.write({'dependency_ids': [(4, task_c.id)]})


class TestSuTaskSubtasks(TransactionCase):
    """Test subtask progress aggregation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['su.project'].create({
            'name': 'Тестовый объект',
        })

    def test_subtask_progress_aggregation(self):
        """Parent progress = avg of children."""
        parent = self.env['su.task'].create({
            'name': 'Родитель',
            'project_id': self.project.id,
        })
        self.env['su.task'].create({
            'name': 'Ребёнок 1',
            'project_id': self.project.id,
            'parent_id': parent.id,
            'progress_manual': 80.0,
        })
        self.env['su.task'].create({
            'name': 'Ребёнок 2',
            'project_id': self.project.id,
            'parent_id': parent.id,
            'progress_manual': 40.0,
        })
        parent.invalidate_recordset()
        self.assertAlmostEqual(parent.progress, 60.0, places=1)

    def test_subtask_progress_excludes_cancelled(self):
        """Cancelled children excluded from avg."""
        parent = self.env['su.task'].create({
            'name': 'Родитель',
            'project_id': self.project.id,
        })
        self.env['su.task'].create({
            'name': 'Ребёнок 1',
            'project_id': self.project.id,
            'parent_id': parent.id,
            'progress_manual': 100.0,
        })
        self.env['su.task'].create({
            'name': 'Ребёнок 2',
            'project_id': self.project.id,
            'parent_id': parent.id,
            'progress_manual': 50.0,
        })
        child_cancelled = self.env['su.task'].create({
            'name': 'Ребёнок 3 (отменён)',
            'project_id': self.project.id,
            'parent_id': parent.id,
            'state': 'cancelled',
            'progress_manual': 0.0,
        })
        parent.invalidate_recordset()
        # (100 + 50) / 2 = 75, not (100 + 50 + 0) / 3
        self.assertAlmostEqual(parent.progress, 75.0, places=1)

    def test_subtask_count(self):
        """subtask_count reflects child count."""
        parent = self.env['su.task'].create({
            'name': 'Родитель',
            'project_id': self.project.id,
        })
        self.env['su.task'].create({
            'name': 'Ребёнок',
            'project_id': self.project.id,
            'parent_id': parent.id,
        })
        parent.invalidate_recordset()
        self.assertEqual(parent.subtask_count, 1)


class TestSuBrigadeComputed(TransactionCase):
    """Test brigade computed fields."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_1 = cls.env['res.users'].create({
            'name': 'Рабочий 1',
            'login': 'worker1_test',
        })
        cls.user_2 = cls.env['res.users'].create({
            'name': 'Рабочий 2',
            'login': 'worker2_test',
        })
        cls.project = cls.env['su.project'].create({
            'name': 'Тестовый объект',
        })

    def test_member_count(self):
        """member_count reflects member_ids length."""
        brigade = self.env['su.brigade'].create({
            'name': 'Бригада',
            'member_ids': [(4, self.user_1.id), (4, self.user_2.id)],
        })
        self.assertEqual(brigade.member_count, 2)

    def test_active_task_count(self):
        """active_task_count counts non-done/cancelled tasks."""
        brigade = self.env['su.brigade'].create({'name': 'Бригада'})
        self.env['su.task'].create({
            'name': 'Новая',
            'project_id': self.project.id,
            'brigade_id': brigade.id,
            'state': 'new',
        })
        self.env['su.task'].create({
            'name': 'В работе',
            'project_id': self.project.id,
            'brigade_id': brigade.id,
            'state': 'in_progress',
        })
        self.env['su.task'].create({
            'name': 'Завершена',
            'project_id': self.project.id,
            'brigade_id': brigade.id,
            'state': 'done',
        })
        self.env['su.task'].create({
            'name': 'Отменена',
            'project_id': self.project.id,
            'brigade_id': brigade.id,
            'state': 'cancelled',
        })
        brigade.invalidate_recordset()
        self.assertEqual(brigade.active_task_count, 2)


class TestSuTaskRBAC(TransactionCase):
    """Test record-level access rules."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['su.project'].create({
            'name': 'Тестовый объект',
        })
        # Foreman user
        cls.foreman_user = cls.env['res.users'].create({
            'name': 'Прораб Иван',
            'login': 'foreman_ivan_test',
            'groups_id': [(4, cls.env.ref('su_base.group_su_foreman').id)],
        })
        # Another foreman
        cls.other_foreman = cls.env['res.users'].create({
            'name': 'Прораб Пётр',
            'login': 'foreman_petr_test',
            'groups_id': [(4, cls.env.ref('su_base.group_su_foreman').id)],
        })
        # Manager user
        cls.manager_user = cls.env['res.users'].create({
            'name': 'Руководитель Мария',
            'login': 'manager_maria_test',
            'groups_id': [(4, cls.env.ref('su_base.group_su_manager').id)],
        })
        cls.brigade_1 = cls.env['su.brigade'].create({
            'name': 'Бригада Ивана',
            'foreman_id': cls.foreman_user.id,
        })
        cls.brigade_2 = cls.env['su.brigade'].create({
            'name': 'Бригада Петра',
            'foreman_id': cls.other_foreman.id,
        })
        cls.task_1 = cls.env['su.task'].create({
            'name': 'Задача бригады 1',
            'project_id': cls.project.id,
            'brigade_id': cls.brigade_1.id,
        })
        cls.task_2 = cls.env['su.task'].create({
            'name': 'Задача бригады 2',
            'project_id': cls.project.id,
            'brigade_id': cls.brigade_2.id,
        })

    def test_foreman_sees_own_brigade_tasks(self):
        """Foreman can read own brigade's tasks."""
        tasks = self.env['su.task'].with_user(
            self.foreman_user
        ).search([('project_id', '=', self.project.id)])
        self.assertIn(self.task_1.id, tasks.ids)

    def test_foreman_cannot_see_other_brigade_tasks(self):
        """Foreman cannot read other brigade's tasks."""
        tasks = self.env['su.task'].with_user(
            self.foreman_user
        ).search([('project_id', '=', self.project.id)])
        self.assertNotIn(self.task_2.id, tasks.ids)

    def test_manager_sees_all_tasks(self):
        """Manager can read all tasks."""
        tasks = self.env['su.task'].with_user(
            self.manager_user
        ).search([('project_id', '=', self.project.id)])
        self.assertIn(self.task_1.id, tasks.ids)
        self.assertIn(self.task_2.id, tasks.ids)


class TestSuTaskNotification(TransactionCase):
    """Test notification on brigade assignment."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['su.project'].create({
            'name': 'Тестовый объект',
        })
        cls.foreman = cls.env['res.users'].create({
            'name': 'Бригадир',
            'login': 'foreman_notif_test',
        })
        cls.brigade = cls.env['su.brigade'].create({
            'name': 'Бригада',
            'foreman_id': cls.foreman.id,
        })

    def test_notification_on_assignment(self):
        """Assigning brigade posts a notification message."""
        task = self.env['su.task'].create({
            'name': 'Задача',
            'project_id': self.project.id,
        })
        initial_count = len(task.message_ids)
        task.write({'brigade_id': self.brigade.id})
        self.assertGreater(len(task.message_ids), initial_count)

    def test_no_notification_on_same_brigade(self):
        """Re-assigning same brigade does not post again."""
        task = self.env['su.task'].create({
            'name': 'Задача',
            'project_id': self.project.id,
            'brigade_id': self.brigade.id,
        })
        initial_count = len(task.message_ids)
        task.write({'brigade_id': self.brigade.id})
        # Same brigade — old == new, no notification
        self.assertEqual(len(task.message_ids), initial_count)
