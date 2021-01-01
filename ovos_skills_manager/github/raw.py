from ovos_skills_manager.github.utils import *
from ovos_skills_manager.utils import desktop_to_json, readme_to_json
from ovos_skills_manager.licenses import get_license_type, is_viral, \
    is_permissive
from ovos_utils.log import LOG
from ovos_utils.json_helper import merge_dict
import json
import yaml
import bs4

# Manual Extraction
GITHUB_README_LOCATIONS = [
    GithubUrls.BLOB + "/" + readme for readme in GITHUB_README_FILES
]

GITHUB_LICENSE_LOCATIONS = [
    GithubUrls.BLOB + "/" + lic for lic in GITHUB_LICENSE_FILES
]

GITHUB_ICON_LOCATIONS = [
    GithubUrls.BLOB + "/res/icon/{repo}",
    GithubUrls.BLOB + "/res/icon/{repo}.png",
    GithubUrls.BLOB + "/res/icon/{repo}.svg",
    GithubUrls.BLOB + "/res/icon/{repo}.jpg"
]

GITHUB_JSON_LOCATIONS = [
    GithubUrls.BLOB + "/res/desktop/skill.json",
    GithubUrls.BLOB + "/skill.json"
]


def cache_repo_requests(url, branch):
    # this looks dumb, but offers a good speed up since this package uses
    # requests_cache
    # TODO solve rate limiting
    # for t in GithubUrls:
    #         def cache():
    #             try:
    #                 match_url_template(url, t, branch)
    #             except GithubInvalidUrl:
    #                 pass
    #             except Exception as e:
    #                 LOG.exception(e)
    #
    #         create_daemon(cache)
    return


def get_repo_releases_from_github_url(url):
    author, repo = author_repo_from_github_url(url)
    normalized_giturl = normalize_github_url(url)
    url = GithubUrls.TAGS.format(author=author, repo=repo)
    html = requests.get(url).text
    soup = bs4.BeautifulSoup(html, 'html.parser')
    urls = ["https://github.com" + a['href'] for a in soup.find_all('a')
            if a['href'].startswith("/" + author)]
    releases = []
    current_release = {}
    # NOTE these are ordered!
    for u in urls:
        if u.startswith(normalized_giturl + "/releases/tag/"):
            current_release["name"] = u.split("/tag/")[-1]
        elif u.startswith(normalized_giturl + "/commit/"):
            current_release["commit"] = {
                "sha": u.split("/commit/")[-1],
                "url": u
            }
        elif u.startswith(normalized_giturl + "/archive"):
            if u.endswith(".zip"):
                current_release["zipball_url"] = u
            elif u.endswith(".tar.gz"):
                current_release["tarball_url"] = u
                # this is always the last field
                releases.append(current_release)
                current_release = {}
    return releases


def get_json_url_from_github_url(url, branch):
    # try default github url
    for template in GITHUB_JSON_LOCATIONS:
        try:
            return match_url_template(url, template, branch)
        except GithubInvalidUrl:
            pass
    # try direct url
    try:
        return blob2raw(url)
    except GithubInvalidUrl:
        if requests.get(url).status_code == 200:
            return url
    raise GithubJsonNotFound


def get_readme_url_from_github_url(url, branch):
    # try url from default github location
    for template in GITHUB_README_LOCATIONS:
        try:
            return match_url_template(url, template, branch)
        except GithubInvalidUrl:
            pass
    # try direct url
    try:
        return blob2raw(url)
    except GithubInvalidUrl:
        if requests.get(url).status_code == 200:
            return url
    raise GithubReadmeNotFound


def get_desktop_url_from_github_url(url, branch):
    # try default github location
    try:
        return match_url_template(url, GithubUrls.DESKTOP_FILE, branch)
    except GithubInvalidUrl:
        pass

    # try direct url
    try:
        return blob2raw(url)
    except GithubInvalidUrl:
        if requests.get(url).status_code == 200:
            return url
    raise GithubDesktopNotFound


def download_url_from_github_url(url, branch):
    # specific file
    try:
        return blob2raw(url)
    except GithubInvalidUrl:
        pass
    # full git repo
    branch = branch or get_branch_from_github_url(url)
    author, repo = author_repo_from_github_url(url)
    url = GithubUrls.DOWNLOAD.format(author=author, branch=branch, repo=repo)
    if requests.get(url).status_code == 200:
        return url
    raise GithubInvalidUrl


def get_icon_url_from_github_url(url, branch):
    try:
        desktop = get_desktop_json_from_github_url(url, branch)
    except GithubDesktopNotFound:
        desktop = {}

    for template in GITHUB_ICON_LOCATIONS:
        try:
            return match_url_template(url, template, branch)
        except GithubInvalidUrl:
            pass

    icon_file = desktop.get("Icon")
    if icon_file:
        # this will assume the icon is in host system, it's not an url
        # lets check if it's present in default github location
        author, repo = author_repo_from_github_url(url)
        url = GithubUrls.ICON.format(author=author, repo=repo,
                                     branch=branch, icon=icon_file)
        if requests.get(url).status_code == 200:
            return blob2raw(url)
        return icon_file
    raise GithubIconNotFound


def get_license_url_from_github_url(url, branch):
    # default github locations
    for template in GITHUB_LICENSE_LOCATIONS:
        try:
            return match_url_template(url, template, branch)
        except GithubInvalidUrl:
            pass
    raise GithubLicenseNotFound


def requirements_url_from_github_url(url, branch):
    # try default github url
    try:
        return match_url_template(url, GithubUrls.REQUIREMENTS, branch)
    except GithubInvalidUrl:
        raise GithubRequirementsNotFound


def skill_requirements_url_from_github_url(url, branch):
    # try default github url
    try:
        return match_url_template(url, GithubUrls.SKILL_REQUIREMENTS, branch)
    except GithubInvalidUrl:
        raise GithubSkillRequirementsNotFound


def manifest_url_from_github_url(url, branch):
    # try default github url
    try:
        return match_url_template(url, GithubUrls.MANIFEST, branch)
    except GithubInvalidUrl:
        raise GithubManifestNotFound


# data getters
def get_requirements_from_github_url(url, branch):
    url = requirements_url_from_github_url(url, branch)
    return [t for t in requests.get(url).text.split("\n")
            if t.strip() and not t.strip().startswith("#")]


def get_skill_requirements_from_github_url(url, branch):
    url = skill_requirements_url_from_github_url(url, branch)
    return [t for t in requests.get(url).text.split("\n")
            if t.strip() and not t.strip().startswith("#")]


def get_manifest_from_github_url(url, branch):
    url = manifest_url_from_github_url(url, branch)
    manifest = requests.get(url).text
    data = yaml.safe_load(manifest)
    if not data:
        # most likely just the template full of comments
        raise InvalidManifest
    if 'dependencies' in data:
        return data
    # some skills in the wild have the manifest without the top-level key
    LOG.warning(
        "{url} contains an invalid manifest, attempting recovery".format(
            url=url))
    recovered = {"dependencies": {}}
    if "python" in data:
        recovered["dependencies"]["python"] = data["python"]
    if "skill" in data:
        recovered["dependencies"]["skill"] = data["skill"]
    if "system" in data:
        recovered["dependencies"]["system"] = data["system"]
    if not len(recovered["dependencies"]):
        # suspicious, doesn't follow standard
        raise InvalidManifest
    return recovered


def get_skill_json_from_github_url(url, branch):
    branch = branch or get_branch_from_github_url(url)
    try:
        url = get_json_url_from_github_url(url, branch)
        url = blob2raw(url)
    except GithubInvalidUrl:
        raise GithubJsonNotFound

    res = requests.get(url).text
    return json.loads(res)


def get_readme_from_github_url(url, branch):
    url = get_readme_url_from_github_url(url, branch)
    return requests.get(url).text


def get_license_from_github_url(url, branch):
    url = get_license_url_from_github_url(url, branch)
    return requests.get(url).text


def get_license_type_from_github_url(url, branch):
    license = get_license_from_github_url(url, branch).lower()
    return get_license_type(license)


def get_license_data_from_github_url(url, branch):
    lic = get_license_from_github_url(url, branch)
    return {
        "license_type": get_license_type(lic),
        "license_text": lic
    }


def get_desktop_from_github_url(url, branch):
    url = get_desktop_url_from_github_url(url, branch)
    return requests.get(url).text


# data parsers
def get_desktop_json_from_github_url(url, branch):
    desktop = get_desktop_from_github_url(url, branch)
    return desktop_to_json(desktop)


def get_readme_json_from_github_url(url, branch):
    readme = get_readme_from_github_url(url, branch)
    return readme_to_json(readme)


def get_requirements_json_from_github_url(url, branch):
    data = {"python": [], "system": {}, "skill": []}
    try:
        manif = get_manifest_from_github_url(url, branch)
        data = manif['dependencies'] or {"python": [], "system": {},
                                         "skill": []}
    except GithubManifestNotFound:
        pass
    try:
        req = get_requirements_from_github_url(url, branch)
        data["python"] = list(set(data["python"] + req))
    except GithubRequirementsNotFound:
        pass
    try:
        skill_req = get_skill_requirements_from_github_url(url, branch)
        data["skill"] = list(set(data["skill"] + skill_req))
    except GithubSkillRequirementsNotFound:
        pass
    return data


def get_skill_from_github_url(url, branch=None):
    # cache_repo_requests(url)  # speed up requests TODO avoid rate limit
    author, repo = author_repo_from_github_url(url)
    data = {
        "authorname": author,
        "foldername": repo,
        "branch": branch,
        "license": "unknown",
        "tags": []
    }
    if not branch:
        try:
            # check if branch is in the url itself
            data["branch"] = branch = get_branch_from_github_url(url)
        except GithubInvalidBranch:
            # let's assume latest release
            try:
                release = get_repo_releases_from_github_url(url)[0]
                data["branch"] = data["version"] = branch = release["name"]
                data["download_url"] = release["tarball_url"]
            except GithubInvalidBranch:
                pass  # unknown branch...

    url = normalize_github_url(url)
    data["url"] = url
    data["skillname"] = skill_name_from_github_url(url)
    data["requirements"] = get_requirements_json_from_github_url(url, branch)

    # augment with json data
    try:
        data = merge_dict(data, get_skill_json_from_github_url(url, branch),
                          merge_lists=True, skip_empty=True, no_dupes=True)
    except GithubJsonNotFound:
        pass

    # augment with readme data
    try:
        readme_data = get_readme_json_from_github_url(url, branch)
        data = merge_dict(data, readme_data,
                          merge_lists=True, skip_empty=True, no_dupes=True)
        # json branch should take precedence? i think so because user
        # explicitly requested it
        branch = readme_data.get("branch") or branch
    except GithubReadmeNotFound:
        pass

    if branch:
        data["branch"] = branch
        data["download_url"] = GithubUrls.DOWNLOAD.format(author=author,
                                                          repo=repo,
                                                          branch=branch)

    try:
        data["license"] = get_license_type_from_github_url(url, branch)
    except GithubLicenseNotFound:
        pass
    try:
        data["icon"] = get_icon_url_from_github_url(url, branch)
    except GithubIconNotFound:
        pass
    # parse bigscreen flags
    if data["requirements"].get("system"):
        data['systemDeps'] = True
    else:
        data['systemDeps'] = False
    try:
        desktop = get_desktop_from_github_url(url, branch)
        data['desktopFile'] = True
    except GithubDesktopNotFound:
        data['desktopFile'] = False

    # augment tags
    if "tags" not in data:
        data["tags"] = []
    if is_viral(data["license"]):
        data["tags"].append("viral-license")
    elif is_permissive(data["license"]):
        data["tags"].append("permissive-license")
    elif "unknown" in data["license"]:
        data["tags"].append("no-license")
    return data