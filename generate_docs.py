import os
import re
import shutil
import subprocess
import sys

import toml


def slugify(s):
    """
    From: http://blog.dolphm.com/slugify-a-string-in-python/

    Simplifies ugly strings into something URL-friendly.
    >>> print slugify("[Some] _ Article's Title--")
    some-articles-title
    """
    s = s.lower()
    for c in [' ', '-', '.', '/']:
        s = s.replace(c, '_')
    s = re.sub('\W', '', s)
    s = s.replace('_', ' ')
    s = re.sub('\s+', ' ', s)
    s = s.strip()
    return s.replace(' ', '-')


class Theme(object):
    def __init__(self, name, path):
        print("Loading %s" % name)
        self.name = name
        self.path = path

        with open(os.path.join(self.path, "theme.toml")) as f:
            self.metadata = toml.load(f)

        with open(os.path.join(self.path, "README.md")) as f:
            self.readme = f.read()
            self.readme = self.readme.replace("{{", "{{/*").replace("}}", "*/}}").replace("{%", "{%/*").replace("%}", "*/%}")

        self.repository = self.get_repository_url()
        self.initial_commit_date, self.last_commit_date = self.get_commit_dates()

    def get_repository_url(self):
        command = "git -C {} remote -v".format(self.path)
        (_, git_remotes) = subprocess.getstatusoutput(command)
        cleaned = (
            git_remotes
            .split("\n")[0]
            .split("\t")[1]
            .replace(" (fetch)", "")
        )
        if cleaned.startswith("git@"):
            cleaned = cleaned.replace("git@github.com:", "https://github.com/").replace(".git", "")
        return cleaned

    def get_commit_dates(self):
        command = 'git log --pretty=format:"%aI" {}'.format(self.path)
        (_, date) = subprocess.getstatusoutput(command)
        dates = date.split("\n")

        # last, first
        return dates[0], dates[len(dates) - 1]

    def to_zola_content(self):
        """
        Returns the page content for Gutenberg
        """
        return """
+++
title = "{title}"
description = "{description}"
template = "theme.html"
date = {updated}

[extra]
created = {created}
updated = {updated}
repository = "{repository}"
homepage = "{homepage}"
minimum_version = "{min_version}"
license = "{license}"
demo = "{demo}"

[extra.author]
name = "{author_name}"
homepage = "{author_homepage}"
+++        

{readme}
        """.format(
            title=self.metadata["name"],
            description=self.metadata["description"],
            created=self.initial_commit_date,
            updated=self.last_commit_date,
            repository=self.repository,
            homepage=self.metadata["homepage"],
            min_version=self.metadata["min_version"],
            license=self.metadata["license"],
            author_name=self.metadata["author"]["name"],
            author_homepage=self.metadata["author"]["homepage"],
            demo=self.metadata.get("demo", ""),
            readme=self.readme,
        )

    def to_zola_folder(self, container):
        """
        Creates the page folder containing the screenshot and the info in
        content/themes
        """
        page_dir = os.path.join(container, self.name)
        os.makedirs(page_dir)

        with open(os.path.join(page_dir, "index.md"), "w") as f:
            f.write(self.to_zola_content())

        shutil.copyfile(
            os.path.join(self.path, "screenshot.png"),
            os.path.join(page_dir, "screenshot.png"),
        )


def read_themes():
    base = "./"
    themes = []

    for item in os.listdir(base):
        full_path = os.path.join(base, item)
        if item == "env":
            continue
        # themes is the name i'm giving locally when building in this folder
        if item.startswith(".") or not os.path.isdir(full_path) or item == "themes":
            continue

        if not os.path.exists(os.path.join(full_path, "screenshot.png")):
            print(" !! Theme {} is missing screenshot.png, skipping !!".format(item))
            continue

        themes.append(Theme(item, full_path))

    return themes


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise Exception("Missing destination folder as argument!")

    destination = sys.argv[1]
    all_themes = read_themes()

    # Delete everything first in this folder
    if os.path.exists(destination):
        shutil.rmtree(destination)
    os.makedirs(destination)

    with open(os.path.join(destination, "_index.md"), "w") as f:
        f.write("""
+++
template = "themes.html"
sort_by = "date"
+++        
        """)

    for t in all_themes:
        t.to_zola_folder(destination)