"""Tests for the database."""


def test_get_close_db(app):
    # Access the database
    with app.app_context():
        session = app.db.session
        assert session is app.db.session
    # Check that the session ended
    assert session is not app.db.session


def test_init_db_command(runner, monkeypatch):
    class Recorder:
        called = False

    def mock_init_db():
        Recorder.called = True

    monkeypatch.setattr('monopyly.database.init_db', mock_init_db)
    result = runner.invoke(args=['init-db'])
    assert 'Initialized' in result.output
    assert Recorder.called

